#!/usr/bin/env python3
"""Agent-free baseline — does a repo run *today*, following its own instructions,
with NO expert repair? This is the DECAY signal (`naive_runs`) for the principled
sample: the counterfactual Lazarus is measured against.

    python benchmark/baseline.py --frame benchmark/frame.json \
        --docker-host ssh://you@box --out benchmark/baseline.json

Fixed protocol, per repo, in a fresh container, hard 30-min cap (watchdog):
  1. clone (shallow).
  2. install from the repo's own files, no repair: environment.yml (conda) |
     requirements.txt | pip install . | R DESCRIPTION.
  3. run a shipped example: examples/demo/tutorial script | `<pkg> --help` /
     `python -m <pkg>`. naive_runs = an example ran to exit 0 with output.
Every stop is recorded with the stage + reason. This is a *conservative* lower
bound on runnability (it only tries the repo's own artefacts) — applied uniformly,
it's a fair contrast to the agent, whose value-add is exactly the repair it skips.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

UA = {"User-Agent": "lazarus-benchmark/0.2"}

# A naive user copies the README's *usage* example — not an install block. Extract
# the first fenced code block that runs the method (skipping install/shell blocks).
_INSTALL_RE = re.compile(r"pip[0-9]? install|python -m pip|conda (install|env|create)|"
                         r"install\.packages|install_github|install_bitbucket|devtools::install|"
                         r"remotes::install|BiocManager::install|R CMD INSTALL|setup\.py|"
                         r"apt(-get)? |git clone|wget |curl |cmake|\bmake\b|npm install|docker ", re.I)
_RUN_RE = re.compile(r"\bimport \b|\bfrom \w+ import|Rscript|python[0-9 ]|"
                     r"\w+\.\w+\(|\w+\s*<-\s*|\w+\(", re.I)
# lines that don't actually run the method (help/load/version calls)
_TRIVIAL_RE = re.compile(r"^\s*(help|vignette|browseVignettes|\?|library|require|"
                         r"sessionInfo|citation|packageVersion|install\.packages)\s*[\(A-Za-z]", re.I)


def readme_example(text: str) -> Optional[str]:
    """Return the code of the README's first runnable, non-install, non-trivial block
    (the language is the repo's primary language, decided by the caller)."""
    for block in re.findall(r"```[A-Za-z0-9]*\n(.*?)```", text, re.S):
        b = block.strip()
        if not b or _INSTALL_RE.search(b) or not _RUN_RE.search(b):
            continue
        lines = [ln for ln in b.splitlines()
                 if ln.strip() and not ln.strip().startswith(("$", "//", "%", "!", ">>>", "R>", "#"))]
        if not any(not _TRIVIAL_RE.match(ln) for ln in lines):  # only help()/library()/… → not a real example
            continue
        code = "\n".join(lines).strip()
        if code:
            return code
    return None


def fetch_readme(slug: str, timeout: float = 20) -> str:
    for branch in ("HEAD",):
        for name in ("README.md", "README.rst", "README.txt", "readme.md"):
            try:
                req = urllib.request.Request(
                    f"https://raw.githubusercontent.com/{slug}/{branch}/{name}", headers=UA)
                with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
                    return r.read().decode("utf-8", "ignore")
            except Exception:  # noqa: BLE001
                continue
    return ""

# --- base image by primary language (pure) ---------------------------------
_PY = {"python", "jupyter notebook", "cython"}
_R = {"r", "rmarkdown"}


def primary_language(langs: dict) -> str:
    if not langs:
        return "python"
    top = max(langs, key=langs.get).lower()
    if top in _R:
        return "r"
    if top in _PY:
        return "python"
    return "python"  # default runtime; the install step still adapts to the repo's files


def base_image_for(lang: str) -> str:
    return {"r": "rocker/r-ver:4.2.0", "python": "continuumio/miniconda3"}[lang]


def github_languages(slug: str, timeout: float = 20) -> dict:
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{slug}/languages", headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return json.loads(r.read())
    except Exception:  # noqa: BLE001
        return {}


# --- the in-container protocol (mechanical; prints a machine-readable verdict) ---
PROTOCOL = r"""
set +e
export DEBIAN_FRONTEND=noninteractive PIP_DISABLE_PIP_VERSION_CHECK=1
command -v git >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq git) >/dev/null 2>&1
verdict() { echo "===BASELINE=== naive_runs=$1 stage=$2 reason=$3"; exit 0; }

git clone --depth 1 "REPO_URL" /repo >/tmp/clone.log 2>&1 || verdict 0 clone clone_failed
cd /repo

# --- install (from the repo's own files, no repair) ---
if [ -f environment.yml ]; then
  timeout 1000 conda env create -q -f environment.yml -p /repo/.env >/tmp/inst.log 2>&1 || verdict 0 install conda_env_failed
  source activate /repo/.env 2>/dev/null || true
elif [ -f requirements.txt ]; then
  timeout 900 pip install -q -r requirements.txt >/tmp/inst.log 2>&1 || verdict 0 install pip_requirements_failed
elif [ -f setup.py ] || [ -f pyproject.toml ]; then
  timeout 900 pip install -q . >/tmp/inst.log 2>&1 || verdict 0 install pip_install_failed
elif [ -f DESCRIPTION ]; then
  RPKG=$(grep -i '^Package:' DESCRIPTION | head -1 | sed 's/[Pp]ackage:[[:space:]]*//' | tr -d '\r')
  # install AND verify the package is actually available (install_local only *warns* on a
  # failed build, so a missing package after install is a real install failure).
  timeout 1200 Rscript -e "if(!requireNamespace('remotes',quietly=TRUE))install.packages('remotes',repos='https://cloud.r-project.org'); remotes::install_local('.',dependencies=TRUE,upgrade='never',build=FALSE); if(!requireNamespace('$RPKG',quietly=TRUE)) quit(status=3)" >/tmp/inst.log 2>&1 || { echo "INSTLOG:"; tail -4 /tmp/inst.log; verdict 0 install R_install_failed; }
else
  verdict 0 install no_install_manifest
fi

# --- find + run a shipped example (what a naive user runs); NOT test files ---
EX=""
for d in example examples demo demos tutorial tutorials quickstart getting_started vignettes; do
  for pat in "*.py" "*.R" "*.r" "*.sh"; do
    f=$(ls $d/$pat 2>/dev/null | grep -vi test | head -1)
    if [ -n "$f" ]; then
      case "$f" in *.py) EX="python $f";; *.R|*.r) EX="Rscript $f";; *.sh) EX="bash $f";; esac
      break 2
    fi
  done
done
# else the README's first non-install usage block (injected; run in the repo's language)
IMPORTONLY=""
if [ -z "$EX" ] && [ -n "README_B64" ]; then
  echo "README_B64" | base64 -d > /repo/.naive_example
  if [ "PRIMARY_LANG" = "r" ]; then EX="Rscript /repo/.naive_example"; else EX="python /repo/.naive_example"; fi
fi
# else: does it at least import / load? (a weaker "runs today"; language-aware)
if [ -z "$EX" ]; then
  if [ -f DESCRIPTION ]; then
    P=$(grep -i '^Package:' DESCRIPTION | head -1 | sed 's/[Pp]ackage:[[:space:]]*//' | tr -d '\r')
    EX="Rscript -e 'library($P)'"; IMPORTONLY=1
  else
    P=""; for d in */; do [ -f "${d}__init__.py" ] && P="${d%/}" && break; done
    [ -z "$P" ] && P=$(basename "$(pwd)" | tr '-' '_')
    EX="python -c 'import $P'"; IMPORTONLY=1
  fi
fi
[ -z "$EX" ] && verdict 0 example no_example_found

echo "RAN: $EX"
cd /repo && timeout 900 bash -lc "$EX" >/tmp/ex.out 2>/tmp/ex.log; RC=$?
# a shipped example (or import) completing without error = it ran (output is often a file)
if [ $RC -eq 0 ]; then
  [ -n "$IMPORTONLY" ] && verdict 1 example imports_only || verdict 1 example ran_ok
else
  echo "EXLOG_TAIL:"; tail -10 /tmp/ex.log 2>/dev/null; echo "INSTLOG_TAIL:"; tail -4 /tmp/inst.log 2>/dev/null
  verdict 0 example "example_exit_${RC}"
fi
"""


@dataclass
class NaiveResult:
    repo_url: str
    naive_runs: Optional[bool] = None
    installed: Optional[bool] = None   # did install SUCCEED? (robust decay signal; less
    stage: str = ""                     # noisy than naive_runs, which also needs a runnable example)
    reason: str = ""
    lang: str = ""
    wall_clock_s: float = 0.0
    log_tail: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def naive_run_one(repo_url: str, *, docker_host: Optional[str], timeout_s: int = 1800) -> NaiveResult:
    from lazarus.sandbox import DockerClient, Sandbox, find_docker

    slug = "/".join(repo_url.rstrip("/").split("/")[-2:])
    lang = primary_language(github_languages(slug))
    res = NaiveResult(repo_url=repo_url, lang=lang)
    code = readme_example(fetch_readme(slug))
    b64 = base64.b64encode(code.encode()).decode() if code else ""
    script = (PROTOCOL.replace("REPO_URL", repo_url)
              .replace("README_B64", b64).replace("PRIMARY_LANG", lang))
    t0 = time.time()
    client = DockerClient(binary=find_docker(), docker_host=docker_host)
    sb = Sandbox(client, base_image_for(lang), workdir="/")
    fired = threading.Event()
    done = threading.Event()

    def _watchdog():
        if done.wait(timeout_s):
            return
        fired.set()
        # A single `docker rm -f` over a flaky ssh:// can hang or fail, and one swallowed
        # failure lets the capped run continue unbounded (observed: a repo stuck 2.5h under a
        # 30m cap). Force-remove by name with a per-attempt timeout, retried until it's gone.
        deadline = time.time() + 180
        while time.time() < deadline and not done.is_set():
            try:
                cr = client.run(["rm", "-f", sb.name], timeout=30)
                if cr.ok or "No such container" in (cr.stderr or ""):
                    sb.started = False
                    return
            except Exception:  # noqa: BLE001 — a hung/failed kill just means: retry
                pass
            time.sleep(3)

    threading.Thread(target=_watchdog, daemon=True).start()
    try:
        sb.start()
        cr = sb.exec(script, timeout=timeout_s + 60)
        out = (cr.stdout or "") + "\n" + (cr.stderr or "")
        res.log_tail = out[-1500:]
        m = re.search(r"===BASELINE===\s+naive_runs=(\d)\s+stage=(\S+)\s+reason=(\S+)", out)
        if m:
            res.naive_runs = m.group(1) == "1"
            res.stage, res.reason = m.group(2), m.group(3)
        elif fired.is_set():
            res.naive_runs, res.stage, res.reason = False, "timeout", "hard_cap"
        else:
            res.naive_runs, res.stage, res.reason = None, "unknown", "no_verdict_parsed"
    except Exception as exc:  # noqa: BLE001
        res.naive_runs = False if fired.is_set() else None
        res.stage, res.reason = ("timeout", "hard_cap") if fired.is_set() else ("error", str(exc)[:80])
    finally:
        done.set()
        try:
            sb.stop()
        except Exception:  # noqa: BLE001
            pass
    res.wall_clock_s = time.time() - t0
    # install SUCCEEDED iff we reached the example stage; FAILED at clone/install; and is
    # INCONCLUSIVE (None) on timeout/error — those are excluded from the decay denominator,
    # not miscounted as decayed. `installed` is the robust decay signal (naive_runs also needs
    # a runnable example, which over-reports decay when the example needs args/data — see pilot).
    if res.stage == "example":
        res.installed = True
    elif res.reason == "no_install_manifest":
        res.installed = None   # not a standard installable package (workflow/C++/subdir) → N/A, excluded
    elif res.stage in ("install", "clone"):
        res.installed = False
    # else timeout/error/unknown → installed stays None (inconclusive)
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="agent-free baseline (naive_runs)")
    ap.add_argument("--frame", default="benchmark/frame.json")
    ap.add_argument("--url", action="append", help="a single repo (repeatable); overrides --frame")
    ap.add_argument("--docker-host", default=None)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--out", default="benchmark/baseline.json")
    args = ap.parse_args(argv)

    urls = list(args.url or [])
    if not urls:
        urls = [s["repo_url"] for s in json.loads(Path(args.frame).read_text())["sample"]]

    rows = json.loads(Path(args.out).read_text()) if Path(args.out).exists() else []
    done_urls = {r["repo_url"] for r in rows}
    for url in urls:
        if url in done_urls:
            print(f"skip (done): {url}"); continue
        print(f"\n=== baseline: {url} ===", flush=True)
        r = naive_run_one(url, docker_host=args.docker_host, timeout_s=args.timeout)
        rows = [x for x in rows if x["repo_url"] != url] + [r.to_dict()]
        Path(args.out).write_text(json.dumps(rows, indent=2, ensure_ascii=False))
        print(f"  -> naive_runs={r.naive_runs}  ({r.stage}/{r.reason}, {r.lang}, {r.wall_clock_s:.0f}s)")
    ran = sum(1 for r in rows if r.get("naive_runs"))
    print(f"\nbaseline: {ran}/{len(rows)} run out of the box  (decay = {100*(1-ran/len(rows)):.0f}%)"
          if rows else "no repos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
