"""Agent-free **decay check** — does a repo still install and run *today*, following
its own instructions, with no expert repair? This is the shipped, importable version
of the benchmark's ``naive_runs`` signal (``benchmark/baseline.py`` is the batch
harness; this module is what ``lazarus decay-check`` and the GitHub Action use).

Fixed protocol, no repair:
  1. shallow-clone the repo
  2. install from its own files: environment.yml (conda) | requirements.txt |
     ``pip install .`` | R ``DESCRIPTION`` — whichever is present, first match wins
  3. run a shipped example (examples/demo/tutorial script), else the README's first
     runnable usage block, else a bare import/load. ``naive_runs`` = it exited 0.

Two sandboxes:
  * ``host``   — run on the current machine (a fresh CI runner *is* the clean env);
    Python installs into a throwaway venv, R into a temp library. Light, no images.
  * ``docker`` — run inside a fresh ``continuumio/miniconda3`` / ``rocker/r-ver``
    container (strict parity with the published benchmark).

It's a conservative lower bound on runnability — it only tries the repo's own
artefacts — so, applied uniformly, it's a fair contrast to what the agent repairs.

NOTE: the pure helpers here are intentionally duplicated in ``benchmark/baseline.py``
(a dev script that predates the package); a future cleanup can point it at this module.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import threading
import time
import urllib.request
from dataclasses import asdict, dataclass
from typing import Optional

UA = {"User-Agent": "lazarus-decaycheck"}

# A naive user copies the README's *usage* example, not an install block.
_INSTALL_RE = re.compile(r"pip[0-9]? install|python -m pip|conda (install|env|create)|"
                         r"install\.packages|install_github|install_bitbucket|devtools::install|"
                         r"remotes::install|BiocManager::install|R CMD INSTALL|setup\.py|"
                         r"apt(-get)? |git clone|wget |curl |cmake|\bmake\b|npm install|docker ", re.I)
_RUN_RE = re.compile(r"\bimport \b|\bfrom \w+ import|Rscript|python[0-9 ]|"
                     r"\w+\.\w+\(|\w+\s*<-\s*|\w+\(", re.I)
_TRIVIAL_RE = re.compile(r"^\s*(help|vignette|browseVignettes|\?|library|require|"
                         r"sessionInfo|citation|packageVersion|install\.packages)\s*[\(A-Za-z]", re.I)

_PY_LANGS = {"python", "jupyter notebook", "cython"}
_R_LANGS = {"r", "rmarkdown"}

VERDICT_RE = re.compile(r"===DECAY===\s+naive_runs=(\d)\s+stage=(\S+)\s+reason=(\S+)")


def readme_example(text: str) -> Optional[str]:
    """The README's first runnable, non-install, non-trivial fenced code block."""
    for block in re.findall(r"```[A-Za-z0-9]*\n(.*?)```", text, re.S):
        b = block.strip()
        if not b or _INSTALL_RE.search(b) or not _RUN_RE.search(b):
            continue
        lines = [ln for ln in b.splitlines()
                 if ln.strip() and not ln.strip().startswith(("$", "//", "%", "!", ">>>", "R>", "#"))]
        if not any(not _TRIVIAL_RE.match(ln) for ln in lines):
            continue
        code = "\n".join(lines).strip()
        if code:
            return code
    return None


def primary_language(langs: dict) -> str:
    if not langs:
        return "python"
    top = max(langs, key=langs.get).lower()
    if top in _R_LANGS:
        return "r"
    return "python"  # default runtime; the install step still adapts to the repo's files


def base_image_for(lang: str) -> str:
    return {"r": "rocker/r-ver:4.2.0", "python": "continuumio/miniconda3"}[lang]


def _slug(repo_url: str) -> str:
    return "/".join(repo_url.rstrip("/").split("/")[-2:])


def _get(url: str, timeout: float = 20) -> Optional[bytes]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:  # noqa: S310
            return r.read()
    except Exception:  # noqa: BLE001
        return None


def github_languages(slug: str) -> dict:
    raw = _get(f"https://api.github.com/repos/{slug}/languages")
    try:
        return json.loads(raw) if raw else {}
    except ValueError:
        return {}


def fetch_readme(slug: str) -> str:
    for name in ("README.md", "README.rst", "README.txt", "readme.md"):
        raw = _get(f"https://raw.githubusercontent.com/{slug}/HEAD/{name}")
        if raw:
            return raw.decode("utf-8", "ignore")
    return ""


# ---------------------------------------------------------------------------
# The protocol: a preamble (clone + install, per sandbox) + a shared body
# (find and run an example). It prints one machine-readable ===DECAY=== line.
# Placeholders REPO_URL / README_B64 / PRIMARY_LANG are substituted per repo.
# ---------------------------------------------------------------------------
_HEAD = r"""
set +e
export PIP_DISABLE_PIP_VERSION_CHECK=1
verdict() { echo "===DECAY=== naive_runs=$1 stage=$2 reason=$3"; exit 0; }
TO="timeout 1200"; command -v timeout >/dev/null 2>&1 || TO=""
command -v git >/dev/null 2>&1 || verdict 0 clone needs_git
"""

_PREAMBLE_DOCKER = _HEAD + r"""
export DEBIAN_FRONTEND=noninteractive
REPODIR=/repo; PY=python; RSCRIPT=Rscript
git clone --depth 1 "REPO_URL" "$REPODIR" >/tmp/clone.log 2>&1 || verdict 0 clone clone_failed
cd "$REPODIR"
if [ -f environment.yml ]; then
  $TO conda env create -q -f environment.yml -p /repo/.env >/tmp/inst.log 2>&1 || verdict 0 install conda_env_failed
  source activate /repo/.env 2>/dev/null || true
elif [ -f requirements.txt ]; then
  $TO pip install -q -r requirements.txt >/tmp/inst.log 2>&1 || verdict 0 install pip_requirements_failed
elif [ -f setup.py ] || [ -f pyproject.toml ]; then
  $TO pip install -q . >/tmp/inst.log 2>&1 || verdict 0 install pip_install_failed
elif [ -f DESCRIPTION ]; then
  RPKG=$(grep -i '^Package:' DESCRIPTION | head -1 | sed 's/[Pp]ackage:[[:space:]]*//' | tr -d '\r')
  $TO Rscript -e "if(!requireNamespace('remotes',quietly=TRUE))install.packages('remotes',repos='https://cloud.r-project.org'); remotes::install_local('.',dependencies=TRUE,upgrade='never'); if(!requireNamespace('$RPKG',quietly=TRUE)) quit(status=3)" >/tmp/inst.log 2>&1 || verdict 0 install R_install_failed
else
  verdict 0 install no_install_manifest
fi
"""

_PREAMBLE_HOST = _HEAD + r"""
WORK=$(mktemp -d); trap 'rm -rf "$WORK"' EXIT
REPODIR="$WORK/repo"; PY=python3; RSCRIPT=Rscript
git clone --depth 1 "REPO_URL" "$REPODIR" >/tmp/decay_clone.log 2>&1 || verdict 0 clone clone_failed
cd "$REPODIR"
if [ -f environment.yml ]; then
  command -v conda >/dev/null 2>&1 || verdict 0 install needs_conda
  $TO conda env create -q -f environment.yml -p "$WORK/.env" >/tmp/decay_inst.log 2>&1 || verdict 0 install conda_env_failed
  PY="$WORK/.env/bin/python"
elif [ -f requirements.txt ] || [ -f setup.py ] || [ -f pyproject.toml ]; then
  python3 -m venv "$WORK/.venv" >/tmp/decay_venv.log 2>&1 || verdict 0 install venv_failed
  PY="$WORK/.venv/bin/python"
  "$PY" -m pip install -q --upgrade pip >/dev/null 2>&1
  if [ -f requirements.txt ]; then
    $TO "$PY" -m pip install -q -r requirements.txt >/tmp/decay_inst.log 2>&1 || verdict 0 install pip_requirements_failed
  else
    $TO "$PY" -m pip install -q . >/tmp/decay_inst.log 2>&1 || verdict 0 install pip_install_failed
  fi
elif [ -f DESCRIPTION ]; then
  command -v Rscript >/dev/null 2>&1 || verdict 0 install needs_r
  export R_LIBS_USER="$WORK/rlib"; mkdir -p "$R_LIBS_USER"
  RPKG=$(grep -i '^Package:' DESCRIPTION | head -1 | sed 's/[Pp]ackage:[[:space:]]*//' | tr -d '\r')
  $TO Rscript -e "if(!requireNamespace('remotes',quietly=TRUE))install.packages('remotes',repos='https://cloud.r-project.org'); remotes::install_local('.',dependencies=TRUE,upgrade='never'); if(!requireNamespace('$RPKG',quietly=TRUE)) quit(status=3)" >/tmp/decay_inst.log 2>&1 || verdict 0 install R_install_failed
else
  verdict 0 install no_install_manifest
fi
"""

_BODY = r"""
EX=""
for d in example examples demo demos tutorial tutorials quickstart getting_started vignettes; do
  for pat in "*.py" "*.R" "*.r" "*.sh"; do
    f=$(ls $d/$pat 2>/dev/null | grep -vi test | head -1)
    if [ -n "$f" ]; then
      case "$f" in *.py) EX="$PY $f";; *.R|*.r) EX="$RSCRIPT $f";; *.sh) EX="bash $f";; esac
      break 2
    fi
  done
done
IMPORTONLY=""
if [ -z "$EX" ] && [ -n "README_B64" ]; then
  echo "README_B64" | base64 -d > "$REPODIR/.naive_example"
  if [ "PRIMARY_LANG" = "r" ]; then EX="$RSCRIPT $REPODIR/.naive_example"; else EX="$PY $REPODIR/.naive_example"; fi
fi
if [ -z "$EX" ]; then
  if [ -f DESCRIPTION ]; then
    P=$(grep -i '^Package:' DESCRIPTION | head -1 | sed 's/[Pp]ackage:[[:space:]]*//' | tr -d '\r')
    EX="$RSCRIPT -e 'library($P)'"; IMPORTONLY=1
  else
    P=""; for d in */; do [ -f "${d}__init__.py" ] && P="${d%/}" && break; done
    [ -z "$P" ] && P=$(basename "$(pwd)" | tr '-' '_')
    EX="$PY -c 'import $P'"; IMPORTONLY=1
  fi
fi
[ -z "$EX" ] && verdict 0 example no_example_found
echo "RAN: $EX"
$TO bash -lc "$EX" >/tmp/decay_ex.out 2>/tmp/decay_ex.log; RC=$?
if [ $RC -eq 0 ]; then
  [ -n "$IMPORTONLY" ] && verdict 1 example imports_only || verdict 1 example ran_ok
else
  echo "EXLOG_TAIL:"; tail -10 /tmp/decay_ex.log 2>/dev/null
  verdict 0 example "example_exit_${RC}"
fi
"""


def build_script(repo_url: str, *, sandbox: str, lang: str, readme_code: Optional[str]) -> str:
    preamble = _PREAMBLE_HOST if sandbox == "host" else _PREAMBLE_DOCKER
    b64 = base64.b64encode(readme_code.encode()).decode() if readme_code else ""
    return ((preamble + _BODY)
            .replace("REPO_URL", repo_url)
            .replace("README_B64", b64)
            .replace("PRIMARY_LANG", lang))


def parse_verdict(output: str):
    """→ (naive_runs: bool, stage, reason) or None if no verdict line was printed."""
    m = VERDICT_RE.search(output or "")
    if not m:
        return None
    return m.group(1) == "1", m.group(2), m.group(3)


@dataclass
class DecayResult:
    repo_url: str
    naive_runs: Optional[bool] = None
    stage: str = ""
    reason: str = ""
    lang: str = ""
    sandbox: str = ""
    wall_clock_s: float = 0.0
    log_tail: str = ""

    @property
    def decayed(self) -> bool:
        """True iff we got a verdict and it did NOT run (an inconclusive run is not 'decayed')."""
        return self.naive_runs is False

    def to_dict(self) -> dict:
        return asdict(self)


def _run_host(script: str, timeout_s: int) -> tuple[str, bool]:
    try:
        cp = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                            timeout=timeout_s)
        return (cp.stdout or "") + "\n" + (cp.stderr or ""), False
    except subprocess.TimeoutExpired as e:
        return ((e.stdout or "") if isinstance(e.stdout, str) else "") + "\n[timed out]", True


def _run_docker(script: str, lang: str, docker_host: Optional[str], timeout_s: int) -> tuple[str, bool]:
    from lazarus.sandbox import DockerClient, Sandbox, find_docker

    client = DockerClient(binary=find_docker(), docker_host=docker_host)
    sb = Sandbox(client, base_image_for(lang), workdir="/")
    fired, done = threading.Event(), threading.Event()

    def _watchdog():
        if done.wait(timeout_s):
            return
        fired.set()
        try:
            sb.stop()
        except Exception:  # noqa: BLE001
            pass

    threading.Thread(target=_watchdog, daemon=True).start()
    try:
        sb.start()
        cr = sb.exec(script, timeout=timeout_s + 60)
        return (cr.stdout or "") + "\n" + (cr.stderr or ""), fired.is_set()
    finally:
        done.set()
        try:
            sb.stop()
        except Exception:  # noqa: BLE001
            pass


def decay_check(repo_url: str, *, sandbox: str = "host", docker_host: Optional[str] = None,
                timeout_s: int = 1800) -> DecayResult:
    """Run the fixed decay protocol against ``repo_url`` and return the verdict."""
    slug = _slug(repo_url)
    lang = primary_language(github_languages(slug))
    res = DecayResult(repo_url=repo_url, lang=lang, sandbox=sandbox)
    script = build_script(repo_url, sandbox=sandbox, lang=lang, readme_code=readme_example(fetch_readme(slug)))
    t0 = time.time()
    try:
        if sandbox == "host":
            out, timed_out = _run_host(script, timeout_s)
        else:
            out, timed_out = _run_docker(script, lang, docker_host, timeout_s)
        res.log_tail = out[-1500:]
        parsed = parse_verdict(out)
        if parsed is not None:
            res.naive_runs, res.stage, res.reason = parsed
        elif timed_out:
            res.naive_runs, res.stage, res.reason = False, "timeout", "hard_cap"
        else:
            res.naive_runs, res.stage, res.reason = None, "unknown", "no_verdict_parsed"
    except Exception as exc:  # noqa: BLE001
        res.naive_runs, res.stage, res.reason = None, "error", str(exc)[:80]
    res.wall_clock_s = time.time() - t0
    return res
