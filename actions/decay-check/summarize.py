#!/usr/bin/env python3
"""Turn a `lazarus decay-check --json` result into GitHub Action outputs + a job
summary. Called by action.yml as: python summarize.py <result.json>."""
import json
import os
import sys


def _append(env_var: str, text: str) -> None:
    path = os.environ.get(env_var)
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)


def main() -> int:
    try:
        d = json.load(open(sys.argv[1], encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a crash upstream leaves no/partial JSON
        d = {}

    runs = d.get("naive_runs")
    _append("GITHUB_OUTPUT",
            f"naive_runs={str(runs).lower()}\n"
            f"stage={d.get('stage', '')}\n"
            f"reason={d.get('reason', '')}\n")

    verdict = "✅ RUNS" if runs is True else ("❌ DECAYED" if runs is False else "⚠️ INCONCLUSIVE")
    secs = float(d.get("wall_clock_s") or 0)
    lines = [
        "## 🧬 Lazarus decay-check",
        "",
        f"**{verdict}** — `{d.get('repo_url', '?')}`",
        "",
        f"- stage / reason: `{d.get('stage', '?')}/{d.get('reason', '?')}`",
        f"- {d.get('lang', '?')} · {d.get('sandbox', '?')} sandbox · {secs:.0f}s",
    ]
    if runs is False:
        lines += ["", "> This repo doesn't run on its own. **Lazarus can revive it** → "
                  "https://doctordean.github.io/lazarus/"]
    _append("GITHUB_STEP_SUMMARY", "\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
