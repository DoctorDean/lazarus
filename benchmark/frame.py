#!/usr/bin/env python3
"""Enumerate the principled-sample frame and draw a seeded random sample.

Frame: journal *Bioinformatics* (Oxford, ISSN 1367-4803), 2018–2021, papers whose
indexed text (OA full text or abstract, via Europe PMC) links a public GitHub repo.

    python benchmark/frame.py --n 20 --seed 42 --out benchmark/frame.json

Pure stdlib (no agent/Docker). Makes polite HTTP calls to Europe PMC + github.com.
Sampling: shuffle the whole population with the seed, then screen in order (extract
a repo → confirm it's public) and keep the first N that pass — a random sample with
inclusion screening. Every screened-out paper is logged with a reason.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter

EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest"
UA = {"User-Agent": "lazarus-benchmark/0.2 (computational-biology reproducibility research)"}
GH_RE = re.compile(r"github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38})?)/([A-Za-z0-9_.\-]+)", re.I)
BAD_OWNERS = {"about", "features", "pricing", "marketplace", "sponsors", "topics",
              "collections", "readme", "site", "orgs", "apps", "settings", "notifications"}
BAD_REPOS = {"issues", "blob", "tree", "wiki", "raw", "releases", "pulls", "commits", "actions"}


def _get(url: str, timeout: float = 40) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as fh:  # noqa: S310 (trusted hosts)
        return fh.read()


def enumerate_population(max_papers: int = 4000) -> tuple[list[dict], int]:
    """All Bioinformatics 2018–2021 papers whose text mentions github."""
    q = 'ISSN:"1367-4803" AND PUB_YEAR:[2018 TO 2021] AND github'
    cursor, out, total = "*", [], 0
    while len(out) < max_papers:
        # resultType=core carries abstractText — where these Applications Notes put
        # their "Availability: github.com/..." link, so no full-text fetch is needed.
        url = (f"{EPMC}/search?query={urllib.parse.quote(q)}&resultType=core"
               f"&format=json&pageSize=100&cursorMark={urllib.parse.quote(cursor)}")
        data = json.loads(_get(url))
        total = data.get("hitCount", total)
        hits = data.get("resultList", {}).get("result", [])
        if not hits:
            break
        for h in hits:
            out.append({"id": h.get("id"), "source": h.get("source"), "pmcid": h.get("pmcid"),
                        "doi": h.get("doi"), "title": h.get("title", ""), "year": h.get("pubYear"),
                        "abstract": h.get("abstractText", "") or ""})
        nxt = data.get("nextCursorMark")
        if not nxt or nxt == cursor:
            break
        cursor = nxt
        time.sleep(0.34)
    return out, total


def paper_text(rec: dict) -> str:
    """The abstract (carries the Availability github link); OA full text as a bonus."""
    text = rec.get("abstract", "") or ""
    if "github.com" not in text.lower() and rec.get("pmcid"):
        for u in (f"{EPMC}/{rec['source']}/{rec['pmcid']}/fullTextXML",):
            try:
                text += "\n" + _get(u).decode("utf-8", "ignore")
            except Exception:  # noqa: BLE001
                pass
    return text


def extract_repo(text: str) -> str | None:
    cands = []
    for owner, repo in GH_RE.findall(text):
        repo = repo.rstrip(".").removesuffix(".git")
        if owner.lower() in BAD_OWNERS or not repo or repo.lower() in BAD_REPOS:
            continue
        cands.append(f"{owner}/{repo}")
    if not cands:
        return None
    return Counter(cands).most_common(1)[0][0]  # the repo mentioned most often


def repo_public(slug: str, timeout: float = 20) -> bool:
    try:
        req = urllib.request.Request(f"https://github.com/{slug}", headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            return r.status == 200
    except Exception:  # noqa: BLE001 — 404 (private/deleted) raises HTTPError
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="enumerate + sample the principled-sample frame")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-screen", type=int, default=200, help="cap on papers screened")
    ap.add_argument("--out", default="benchmark/frame.json")
    args = ap.parse_args(argv)

    print("enumerating Bioinformatics 2018–2021 (mentions github)…", file=sys.stderr, flush=True)
    pop, total = enumerate_population()
    print(f"population: {len(pop)} enumerated (hitCount {total})", file=sys.stderr, flush=True)

    random.Random(args.seed).shuffle(pop)  # seeded random order → screen in order

    included, excluded, seen_repos = [], [], set()
    for rec in pop:
        if len(included) >= args.n or (len(included) + len(excluded)) >= args.max_screen:
            break
        slug = extract_repo(paper_text(rec))
        if not slug:
            excluded.append({**rec, "reason": "no github repo extracted"})
            continue
        if slug.lower() in seen_repos:
            excluded.append({**rec, "repo": slug, "reason": "duplicate repo"})
            continue
        seen_repos.add(slug.lower())
        if not repo_public(slug):
            excluded.append({**rec, "repo": slug, "reason": "repo not public/does not exist"})
            continue
        included.append({"repo_url": f"https://github.com/{slug}", "title": rec["title"],
                         "year": rec["year"], "doi": rec.get("doi"), "id": rec["id"]})
        print(f"  [{len(included):>2}] {slug:40} {rec['title'][:56]}", file=sys.stderr, flush=True)
        time.sleep(0.2)

    out = {
        "frame": "Bioinformatics (ISSN 1367-4803), 2018–2021, full-text/abstract links a public GitHub repo",
        "seed": args.seed, "population_enumerated": len(pop), "hit_count": total,
        "screened": len(included) + len(excluded), "n": len(included),
        "sample": included, "excluded": excluded,
    }
    import pathlib
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nwrote {args.out}: {len(included)} sampled · {len(excluded)} screened-out "
          f"· population {len(pop)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
