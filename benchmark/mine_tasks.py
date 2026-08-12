#!/usr/bin/env python3
"""Mine benchmark task candidates out of the completed benchmark runs.

What this tool does and does *not* do matters, so it's worth being explicit.

**It does** the mechanical half: gather every repo we have attempted, pin each to the
last commit before a cutoff date (so a task measures a fixed tree, and one that predates
our own give-back PRs), carry over the capability line and domain, and write a review
manifest.

**It does not** invent ground truth. The `reproduced_reported` field in ``results*.json``
is *not* reliable as a benchmark target: across the 67 completed runs, 20 of the 33
non-null values are the agent's own sanity threshold rather than a number from the paper
— 14 of them byte-identical to `sanity_threshold`, the rest round self-consistency bars
(``pearson_r=1``, ``max_abs_diff=0``). Promoting those to task targets would reintroduce
exactly the self-grading that ``task.py`` exists to remove, just laundered through a data
file. So every candidate is classified by how far its ground truth can be trusted, and
anything unverified is written to a manifest for a human — never emitted as a task.

    python benchmark/mine_tasks.py --out benchmark/tasks/CANDIDATES.md

Pins are cached in ``benchmark/tasks/pins.json``, so re-runs cost no API calls and a
sweep interrupted by GitHub's 60/hour unauthenticated limit resumes where it stopped.
"""
from __future__ import annotations

import argparse
import glob
import json
import urllib.error
import urllib.request
from pathlib import Path

# Lazarus work started 2026-07-07; pin strictly before it so no task can be solved by
# a fix we ourselves contributed upstream.
DEFAULT_CUTOFF = "2026-07-01T00:00:00Z"
PINS = Path("benchmark/tasks/pins.json")

# How much a candidate's ground truth can be trusted, worst first.
AGENT_BAR = "agent-bar"      # 'reported' is the agent's own threshold — unusable as-is
CHECK_PAPER = "check-paper"  # plausibly from the paper; a human must confirm it
NO_TARGET = "no-target"      # no reported value at all; needs a hand-built target


def load_runs() -> list:
    rows, seen = [], set()
    for f in sorted(glob.glob("benchmark/results*.json")):
        for r in json.load(open(f)):
            u = r.get("repo_url")
            if not u or u in seen:
                continue
            seen.add(u)
            rows.append(r)
    return rows


def trust_of(row: dict) -> str:
    """Classify how usable a run's reported value is as benchmark ground truth."""
    rep, thr = row.get("reproduced_reported"), row.get("sanity_threshold")
    if rep is None:
        return NO_TARGET
    if thr is not None and float(rep) == float(thr):
        return AGENT_BAR                      # the agent graded itself against its own bar
    if float(rep) in (0.0, 1.0, 100.0):
        return AGENT_BAR                      # round self-consistency bar, not a paper result
    return CHECK_PAPER


def _token() -> str:
    """Optional ``GITHUB_TOKEN``, from the environment or the gitignored ``.env``.

    Anonymous access is 60 requests/hour, which is fine for topping up a pin cache but
    painful for P3's fresh corpus (hundreds of lookups). A token lifts it to 5000/hour.
    Every repo read here is public, so the token needs **no scopes at all**.
    """
    import os

    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    env = Path(".env")
    if env.exists():
        for line in env.read_text(errors="replace").splitlines():
            key, _, val = line.partition("=")
            if key.strip() == "GITHUB_TOKEN":
                return val.strip().strip("'\"")
    return ""


def _api(url: str):
    headers = {"User-Agent": "lazarus-benchmark/0.5",
               "Accept": "application/vnd.github+json"}
    tok = _token()
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as fh:
        return json.load(fh)


def pin_commit(repo_url: str, cutoff: str, cache: dict) -> tuple:
    """Last commit strictly before ``cutoff``. Returns (sha, date) or (None, reason)."""
    if repo_url in cache:
        c = cache[repo_url]
        return c.get("sha"), c.get("date") or c.get("error")
    slug = repo_url.rstrip("/").split("github.com/")[-1].removesuffix(".git")
    try:
        data = _api(f"https://api.github.com/repos/{slug}/commits"
                    f"?until={cutoff}&per_page=1")
    except urllib.error.HTTPError as exc:
        reason = "rate-limited" if exc.code in (403, 429) else f"http {exc.code}"
        return None, reason
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}"
    if not data:
        return None, "no commit before cutoff"
    sha, date = data[0]["sha"], data[0]["commit"]["committer"]["date"]
    cache[repo_url] = {"sha": sha, "date": date}
    return sha, date


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="mine benchmark task candidates")
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    ap.add_argument("--out", default="benchmark/tasks/CANDIDATES.md")
    ap.add_argument("--limit", type=int, default=0, help="cap API lookups this run (rate limit)")
    ap.add_argument("--trust", choices=(AGENT_BAR, CHECK_PAPER, NO_TARGET),
                    help="only mine candidates of this trust class")
    args = ap.parse_args(argv)

    cache = json.loads(PINS.read_text()) if PINS.exists() else {}
    print(f"github auth: {'token (5000/hr)' if _token() else 'anonymous (60/hr)'}")
    rows = load_runs()
    rows = [r for r in rows if not args.trust or trust_of(r) == args.trust]
    rows.sort(key=lambda r: (trust_of(r) != CHECK_PAPER, r.get("name") or ""))

    looked_up = 0
    out = []
    for r in rows:
        trust = trust_of(r)
        sha = date = None
        if r["repo_url"] in cache or not args.limit or looked_up < args.limit:
            was_cached = r["repo_url"] in cache
            sha, date = pin_commit(r["repo_url"], args.cutoff, cache)
            looked_up += 0 if was_cached else 1
        out.append({"row": r, "trust": trust, "sha": sha, "date": date})

    PINS.parent.mkdir(parents=True, exist_ok=True)
    PINS.write_text(json.dumps(cache, indent=2, sort_keys=True))

    pinned = sum(1 for o in out if o["sha"])
    by_trust = {t: sum(1 for o in out if o["trust"] == t) for t in (CHECK_PAPER, AGENT_BAR, NO_TARGET)}

    lines = [
        "# Task candidates — needs review",
        "",
        "Generated by `python benchmark/mine_tasks.py`. **These are not tasks.** Each row",
        "needs a human to supply a ground truth the harness can own before it becomes one",
        "(see `../LEADERBOARD_SCOPE.md` §2.1).",
        "",
        f"- {len(out)} candidates, {pinned} pinned to a commit before `{args.cutoff}`",
        f"- `{CHECK_PAPER}`: {by_trust[CHECK_PAPER]} — a reported value that may be the paper's; **verify against the paper**",
        f"- `{AGENT_BAR}`: {by_trust[AGENT_BAR]} — reported value *is* the agent's own sanity bar; **unusable, needs a real target**",
        f"- `{NO_TARGET}`: {by_trust[NO_TARGET]} — no reported value; needs a hand-built target",
        "",
        "| trust | name | domain | metric | reported | agent bar | commit | repo |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for o in out:
        r = o["row"]
        slug = r["repo_url"].split("github.com/")[-1]
        sha = (o["sha"] or "")[:8] or f"_{o['date'] or 'unpinned'}_"
        lines.append(
            f"| `{o['trust']}` | {r.get('name') or '?'} | {r.get('domain') or '—'} | "
            f"{r.get('sanity_metric') or '—'} | {r.get('reproduced_reported')} | "
            f"{r.get('sanity_threshold')} | `{sha}` | [{slug}]({r['repo_url']}) |")

    Path(args.out).write_text("\n".join(lines) + "\n")
    print(f"{len(out)} candidates -> {args.out}  ({pinned} pinned, {looked_up} API lookups)")
    for t, n in by_trust.items():
        print(f"  {t:<12} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
