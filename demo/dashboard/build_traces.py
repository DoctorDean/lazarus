#!/usr/bin/env python3
"""Bake the dashboard's replay data from REAL benchmark runs.

The harness (benchmark/run.py) streams each resurrection's events to stdout as
``  text: …`` (the agent's reasoning) and ``  tool_use: …`` (its shell/tool calls),
grouped under a ``=== <repo_url> ===`` header. This parses that log, joins each
block with the verified outcome in results_frame.json, and writes a self-contained
``traces.json`` the dashboard replays — so the "Resurrect" feed is the agent's
actual words and commands, ending on the real, independently-verified result.

    python demo/dashboard/build_traces.py --log <harness.out> \
        --results benchmark/results_frame.json --out demo/dashboard/traces.json

Nothing here is synthesized: no log block → no trace (the repo just isn't replayable).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HEADER = re.compile(r"^=== (https?://\S+) ===\s*$")
SKIP = ("claude.ai connectors are disabled", "Permission deny rule", "matches no known tool")


def _tool_label(raw: str) -> str:
    """`mcp__lazarus__sandbox_run({"command": "cd /x && …"})` → a short human line."""
    m = re.match(r"([A-Za-z0-9_]+)\((.*)", raw, re.S)
    name = (m.group(1) if m else raw).replace("mcp__lazarus__", "").replace("ToolSearch", "load tools")
    # surface the shell command / file path when there is one
    cmd = re.search(r'"command"\s*:\s*"(.*?)(?:"|$)', raw, re.S)
    path = re.search(r'"path"\s*:\s*"(.*?)(?:"|$)', raw, re.S)
    tag = re.search(r'"tag"\s*:\s*"(.*?)(?:"|$)', raw, re.S)
    nm = re.search(r'"name"\s*:\s*"(.*?)(?:"|$)', raw, re.S)
    detail = ""
    if cmd:
        detail = cmd.group(1)
    elif path:
        detail = path.group(1)
    elif tag:
        detail = f"snapshot → {tag.group(1)}"
    elif nm:
        detail = nm.group(1)
    detail = detail.replace('\\"', '"').replace("\\n", " ").strip()
    return name, detail


def parse_log(text: str) -> dict[str, list[dict]]:
    """→ {repo_url: [ {kind: 'think'|'act', text, tool?, detail?}, … ]}"""
    traces: dict[str, list[dict]] = {}
    cur: list[dict] | None = None
    for line in text.splitlines():
        h = HEADER.match(line)
        if h:
            cur = traces.setdefault(h.group(1), [])
            continue
        if cur is None or any(s in line for s in SKIP):
            continue
        if line.startswith("  text: "):
            body = line[len("  text: "):].strip()
            if body:
                cur.append({"kind": "think", "text": body})
        elif line.startswith("  tool_use: "):
            name, detail = _tool_label(line[len("  tool_use: "):].strip())
            cur.append({"kind": "act", "text": name, "tool": name, "detail": detail})
    return traces


def build(log_paths: list[Path], results_path: Path) -> dict:
    # later logs override earlier ones per repo (a resume-retry supersedes the
    # original failed attempt), so the replay always shows the run that succeeded.
    traces: dict[str, list[dict]] = {}
    for lp in log_paths:
        for url, steps in parse_log(lp.read_text()).items():
            if steps:
                traces[url] = steps
    results = {r["repo_url"]: r for r in json.loads(results_path.read_text())}
    out: dict[str, dict] = {}
    for url, steps in traces.items():
        r = results.get(url, {})
        # only replayable if it produced a terminal (non-infra) outcome + has real steps
        if not steps or not r or r.get("outcome") in (None, "infra-failed"):
            continue
        out[url] = {
            "repo_url": url,
            "name": r.get("name") or url.rstrip("/").split("/")[-1],
            "outcome": r.get("outcome"),
            "turns": r.get("turns"),
            "wall_clock_s": r.get("wall_clock_s"),
            "cost_usd": r.get("cost_usd"),
            "verified": r.get("verified"),
            "summary": r.get("summary"),
            "sanity_metric": r.get("sanity_metric"),
            "sanity_threshold": r.get("sanity_threshold"),
            "reproduced_measured": r.get("reproduced_measured"),
            "reproduced_reported": r.get("reproduced_reported"),
            "steps": steps,
        }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", required=True, action="append",
                    help="harness stdout log (repeatable; later logs override per repo)")
    ap.add_argument("--results", default="benchmark/results_frame.json")
    ap.add_argument("--out", default="demo/dashboard/traces.json")
    args = ap.parse_args(argv)
    data = build([Path(p) for p in args.log], Path(args.results))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(data, indent=2, ensure_ascii=False))
    total_steps = sum(len(t["steps"]) for t in data.values())
    print(f"wrote {len(data)} replayable traces ({total_steps} real steps) → {args.out}")
    for url, t in sorted(data.items()):
        print(f"  {t['outcome']:11} {len(t['steps']):>3} steps  {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
