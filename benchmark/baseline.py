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
  timeout 1200 Rscript -e 'if(!requireNamespace("remotes",quietly=TRUE))install.packages("remotes",repos="https://cloud.r-project.org");remotes::install_local(".",dependencies=TRUE,upgrade="never")' >/tmp/inst.log 2>&1 || verdict 0 install R_install_failed
else
  verdict 0 install no_install_manifest
fi

# --- find + run a shipped example ---
EX=""
for d in example examples demo demos tutorial tutorials vignettes test tests testthat; do
  for pat in "*.py" "*.R" "*.r" "*.sh"; do
    f=$(ls $d/$pat 2>/dev/null | head -1)
    if [ -n "$f" ]; then
      case "$f" in *.py) EX="python $f";; *.R|*.r) EX="Rscript $f";; *.sh) EX="bash $f";; esac
      break 2
    fi
  done
done
# fallback: a package CLI / module --help (weak, but proves it imports + runs)
if [ -z "$EX" ]; then
  PKG=$(basename $(pwd))
  if [ -d "$PKG" ] && [ -f "$PKG/__init__.py" ]; then EX="python -c 'import $PKG'"; fi
fi
[ -z "$EX" ] && verdict 0 example no_example_found

OUT=$(cd /repo && timeout 900 bash -lc "$EX" 2>/tmp/ex.log)
RC=$?
if [ $RC -eq 0 ] && { [ -n "$OUT" ] || [ -s /tmp/ex.log ]; }; then
  verdict 1 example ran_ok
else
  verdict 0 example "example_exit_${RC}"
fi
"""


@dataclass
class NaiveResult:
    repo_url: str
    naive_runs: Optional[bool] = None
    stage: str = ""
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
    t0 = time.time()
    client = DockerClient(binary=find_docker(), docker_host=docker_host)
    sb = Sandbox(client, base_image_for(lang), workdir="/")
    fired = threading.Event()
    done = threading.Event()

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
        cr = sb.exec(PROTOCOL.replace("REPO_URL", repo_url), timeout=timeout_s + 60)
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
