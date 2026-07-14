#!/usr/bin/env python3
"""Summarise benchmark results into the headline numbers + a table.

    python benchmark/report.py                 # reads benchmark/results.json
    python benchmark/report.py --out benchmark/results.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import SUCCESS, INFRA  # type: ignore  # (run.py sits alongside)


def summarize(rows: list[dict]) -> dict:
    # infra-failed = the harness/host couldn't start; not a method outcome, so it's
    # excluded from the revival-rate denominator (but reported and retryable).
    infra = sum(1 for r in rows if r.get("outcome") in INFRA)
    method = [r for r in rows if r.get("outcome") not in INFRA]
    n = len(method)
    revived = sum(1 for r in method if r.get("outcome") in SUCCESS)
    reproduced = sum(1 for r in method if r.get("outcome") == "reproduced")

    reasons: dict[str, int] = {}
    for r in rows:
        reasons[r.get("outcome", "?")] = reasons.get(r.get("outcome", "?"), 0) + 1

    # decay: fraction that did NOT run without the agent (only over repos with a baseline)
    with_baseline = [r for r in method if r.get("naive_runs") is not None]
    dead = [r for r in with_baseline if not r["naive_runs"]]
    decay_rate = (len(dead) / len(with_baseline)) if with_baseline else None
    # revival rate over the dead ones (if baseline), else over all attempted (method) repos
    if dead:
        revived_dead = sum(1 for r in dead if r.get("outcome") in SUCCESS)
        revival_rate = revived_dead / len(dead)
    else:
        revival_rate = (revived / n) if n else 0.0

    return {
        "attempted": n,
        "infra_failed": infra,
        "revived": revived,
        "reproduced": reproduced,
        "revival_rate": revival_rate,
        "decay_rate": decay_rate,
        "reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
    }


def render(rows: list[dict]) -> str:
    s = summarize(rows)
    out = ["Lazarus benchmark — results", "=" * 30]
    for r in sorted(rows, key=lambda r: r.get("outcome", "")):
        name = r.get("name") or r["repo_url"].rstrip("/").split("/")[-1]
        extra = ""
        if r.get("reproduced_measured") is not None:
            extra = f"  ({r['reproduced_measured']} vs {r['reproduced_reported']})"
        out.append(f"  {r.get('outcome',''):18} {name:24} "
                   f"{r.get('turns',0):>3}t {r.get('wall_clock_s',0):>6.0f}s{extra}")
    out += ["",
            f"attempted     : {s['attempted']}"
            + (f"  (+{s['infra_failed']} infra-failed, retryable, excluded)" if s['infra_failed'] else ""),
            f"revived       : {s['revived']}  (reproduced the paper: {s['reproduced']})",
            f"revival rate  : {s['revival_rate']*100:.0f}%"
            + ("  (of the dead)" if s['decay_rate'] is not None else "  (of attempted)")]
    if s["decay_rate"] is not None:
        out.append(f"decay rate    : {s['decay_rate']*100:.0f}%  (didn't run without the agent)")
    out.append("reasons       : " + ", ".join(f"{k}×{v}" for k, v in s["reasons"].items()))
    return "\n".join(out)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="benchmark/results.json")
    args = ap.parse_args(argv)
    p = Path(args.out)
    rows = json.loads(p.read_text()) if p.exists() else []
    print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
