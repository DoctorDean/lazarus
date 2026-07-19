#!/usr/bin/env python3
"""JOSS sourcing for the cross-domain decay frame (Track 2).

Crossref doesn't carry the software repo for JOSS/SoftwareX (the link lives in the paper
body). JOSS's own API does — `published.json` gives every accepted paper's
`software_repository`, plus `tags` (domain) and `languages`. That makes JOSS the cleanest
*genuinely cross-domain*, repo-guaranteed source (astronomy, ML, chemistry, physics, crypto,
ecology, …), with the metadata to stratify by domain, language, and age.

Scientific note: JOSS *reviews software for runnability*, so it's the low-decay end of the
spectrum — the "reviewed code survives" anchor. Pair it with unreviewed domain venues (where
code is an afterthought) to get the decay contrast that is the cross-domain finding.

    python benchmark/joss.py --n 30 --seed 42 --year-min 2018 --out benchmark/frame_joss.json

Pure stdlib; polite HTTP to joss.theoj.org + github.com. Feeds `lazarus decay-check` (cheap).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame import repo_public  # noqa: E402

JOSS = "https://joss.theoj.org/papers/published.json"
UA = {"User-Agent": "lazarus-benchmark/0.3 (research-code decay study; +https://github.com/DoctorDean/lazarus)"}
GH = re.compile(r"github\.com/([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9_.\-]+)", re.I)


def _get(url: str, timeout: float = 40) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as fh:  # noqa: S310
        return fh.read()


def _csv(s) -> list[str]:
    """JOSS returns tags/languages as comma-separated strings (not arrays)."""
    if isinstance(s, list):
        return [str(x).strip() for x in s if str(x).strip()]
    return [t.strip() for t in (s or "").split(",") if t.strip()]


def github_slug(repo_url: str) -> str | None:
    m = GH.search(repo_url or "")
    if not m:
        return None  # JOSS also hosts gitlab/bitbucket; github-only for now (see TODO)
    return f"{m.group(1)}/{m.group(2).rstrip('.').removesuffix('.git')}"


def iter_published(max_pages: int = 400):
    """Yield accepted JOSS papers, newest first, one page (20) at a time."""
    for page in range(1, max_pages + 1):
        try:
            items = json.loads(_get(f"{JOSS}?page={page}"))
        except Exception:  # noqa: BLE001
            break
        if not items:
            break
        yield from items
        time.sleep(0.3)


def sample(n: int, seed: int, year_min: int | None, allowed_langs: set | None = None) -> tuple[list, dict]:
    """A seeded random sample of github-hosted, public JOSS papers (with domain metadata).

    ``allowed_langs`` (lowercased) filters to repos whose *primary* language decay-check can
    install (Python/R). Keeps "cross-domain" honest: many domains, one install ecosystem —
    so a DECAYED verdict is real decay, not an unsupported build system.
    """
    pool, lang_skip = [], 0
    for p in iter_published():
        if p.get("state") != "accepted":
            continue
        try:
            yr = int(p.get("year") or 0)
        except (TypeError, ValueError):
            yr = 0
        if year_min and yr < year_min:
            continue
        slug = github_slug(p.get("software_repository", ""))
        if not slug:
            continue
        if allowed_langs is not None:
            primary = (_csv(p.get("languages")) or [""])[0].lower()
            if primary not in allowed_langs:
                lang_skip += 1
                continue
        pool.append((slug, p))
    random.Random(seed).shuffle(pool)
    included, seen = [], set()
    for slug, p in pool:
        if len(included) >= n:
            break
        if slug.lower() in seen:
            continue
        seen.add(slug.lower())
        if not repo_public(slug):
            continue
        tags, langs = _csv(p.get("tags")), _csv(p.get("languages"))
        included.append({
            "repo_url": f"https://github.com/{slug}", "venue": "JOSS", "reviewed_software": True,
            "title": p.get("title", ""), "year": yr, "doi": p.get("doi"),
            "tags": tags, "languages": langs,
        })
        print(f"  [{len(included):>2}] {slug:40} {(tags[0] if tags else '?')[:26]:26} {'/'.join(langs[:3])}",
              file=sys.stderr, flush=True)
        time.sleep(0.15)
    spread = {
        "top_tags": Counter(t for s in included for t in s["tags"]).most_common(12),
        "top_languages": Counter(l for s in included for l in s["languages"]).most_common(12),
        "pool_size": len(pool), "language_filtered_out": lang_skip,
    }
    return included, spread


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="draw a seeded cross-domain JOSS sample")
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--year-min", type=int, default=2018)
    ap.add_argument("--languages", default="Python,R,Jupyter Notebook",
                    help="keep only repos whose primary language is one of these "
                         "(what decay-check can install); empty string = no filter")
    ap.add_argument("--out", default="benchmark/frame_joss.json")
    args = ap.parse_args(argv)

    allowed = {s.strip().lower() for s in args.languages.split(",") if s.strip()} or None
    print(f"enumerating JOSS published papers… (languages={sorted(allowed) if allowed else 'all'})",
          file=sys.stderr, flush=True)
    included, spread = sample(args.n, args.seed, args.year_min, allowed)
    out = {"frame": "JOSS (reviewed scientific software; cross-domain, repo-guaranteed)",
           "seed": args.seed, "year_min": args.year_min, "languages": sorted(allowed) if allowed else "all",
           "n": len(included), "domain_spread": spread, "sample": included}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nwrote {args.out}: {len(included)} JOSS repos (pool {spread['pool_size']})",
          file=sys.stderr)
    print("domains:", [t for t, _ in spread["top_tags"][:8]], file=sys.stderr)
    print("languages:", [l for l, _ in spread["top_languages"][:8]], file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
