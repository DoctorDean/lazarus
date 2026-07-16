#!/usr/bin/env python3
"""Summarise benchmark results into the headline numbers + a table.

    python benchmark/report.py                 # reads benchmark/results.json
    python benchmark/report.py --out benchmark/results.json
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import SUCCESS, INFRA  # type: ignore  # (run.py sits alongside)


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% Wilson score interval for a binomial proportion k/n. Preferred over the
    normal approximation at small n and extreme proportions (e.g. 85% of 20)."""
    if n <= 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def merge_baseline(rows: list[dict], baseline_rows: list[dict]) -> list[dict]:
    """Join the agent-free baseline's naive_runs onto the harness rows by repo_url
    (run.py leaves naive_runs=None; the signal lives in baseline_frame.json)."""
    nr = {b["repo_url"]: b.get("naive_runs") for b in baseline_rows}
    out = []
    for r in rows:
        r = dict(r)
        if r.get("naive_runs") is None and r.get("repo_url") in nr:
            r["naive_runs"] = nr[r["repo_url"]]
        out.append(r)
    return out


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
    decay_ci = wilson_ci(len(dead), len(with_baseline))
    # revival rate over the dead ones (if baseline), else over all attempted (method) repos
    if dead:
        revived_dead = sum(1 for r in dead if r.get("outcome") in SUCCESS)
        revival_rate = revived_dead / len(dead)
        revival_ci = wilson_ci(revived_dead, len(dead))
        revival_k, revival_n = revived_dead, len(dead)
    else:
        revival_rate = (revived / n) if n else 0.0
        revival_ci = wilson_ci(revived, n)
        revival_k, revival_n = revived, n

    return {
        "attempted": n,
        "infra_failed": infra,
        "revived": revived,
        "reproduced": reproduced,
        "revival_rate": revival_rate,
        "revival_ci": revival_ci,
        "revival_k": revival_k,
        "revival_n": revival_n,
        "decay_rate": decay_rate,
        "decay_ci": decay_ci,
        "decay_k": len(dead),
        "decay_n": len(with_baseline),
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
    def _ci(ci):
        return f"  [95% CI {ci[0]*100:.0f}–{ci[1]*100:.0f}%]" if ci else ""
    out += ["",
            f"attempted     : {s['attempted']}"
            + (f"  (+{s['infra_failed']} infra-failed, retryable, excluded)" if s['infra_failed'] else ""),
            f"revived       : {s['revived']}  (reproduced the paper: {s['reproduced']})",
            f"revival rate  : {s['revival_rate']*100:.0f}%  ({s['revival_k']}/{s['revival_n']})"
            + _ci(s["revival_ci"])
            + ("  of the dead" if s['decay_rate'] is not None else "  of attempted")]
    if s["decay_rate"] is not None:
        out.append(f"decay rate    : {s['decay_rate']*100:.0f}%  ({s['decay_k']}/{s['decay_n']})"
                   + _ci(s["decay_ci"]) + "  didn't run without the agent")
    out.append("reasons       : " + ", ".join(f"{k}×{v}" for k, v in s["reasons"].items()))
    return "\n".join(out)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="benchmark/results.json")
    ap.add_argument("--baseline", help="baseline JSON to join naive_runs from (decay signal)")
    args = ap.parse_args(argv)
    p = Path(args.out)
    rows = json.loads(p.read_text()) if p.exists() else []
    if args.baseline and Path(args.baseline).exists():
        rows = merge_baseline(rows, json.loads(Path(args.baseline).read_text()))
    print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
