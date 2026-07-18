#!/usr/bin/env python3
"""Track 2 — a **cross-domain** decay frame. Scaffold (seed for the fuller benchmark paper).

The Track-1 frame (`frame.py`) samples one journal in one field. Track 2 asks whether the
85% decay generalises, by sampling *across domains* — and it can be large and cheap because
the **decay** measurement is agent-free (`lazarus decay-check`, ~3 min/repo, ~$0). Only the
(optional) revival half needs the agent.

DESIGN
------
Stratified seeded random sample: draw `--per-stratum` repos from each stratum, same inclusion
screening as Track 1 (paper text links a *public* GitHub repo; de-dup; log every exclusion).

Phase 1 (this scaffold, Europe PMC — works today across computational *life-science* subfields):
  computational biology · bioinformatics methods · genomics · cheminformatics · ecology/evolution
  methods · neuroinformatics. Different venues → real subfield spread within EPMC's coverage.

Phase 2 (TODO — needs a non-EPMC source; EPMC is biomedical):
  astronomy (Astronomy & Computing), machine learning (JMLR / NeurIPS datasets+benchmarks),
  chemistry/physics, and the two repo-guaranteed cross-domain software venues
  **JOSS** (ISSN 2475-9066) and **SoftwareX** (2352-7110). Source via Crossref / venue APIs.

HYPOTHESIS worth stating in the paper: decay likely *varies by venue review model* — venues that
review software for runnability (JOSS/SoftwareX) should decay less than a random ML/astro repo.
That variation is itself a cross-domain finding, not noise.

    python benchmark/frame_crossdomain.py --per-stratum 15 --seed 42 --out benchmark/frame_crossdomain.json

Pure stdlib; polite HTTP to Europe PMC + github.com. Reuses Track-1 screening from frame.py.
Nothing here runs the agent; feed the sampled URLs to `lazarus decay-check` (cheap) and,
selectively, to `benchmark/run.py` (expensive).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame import EPMC, extract_repo, paper_text, repo_public, _get  # noqa: E402
import urllib.parse  # noqa: E402

# Phase-1 strata: (domain label, Europe PMC query). Each targets a distinct computational
# subfield/venue so the sample spans domains, not just one journal. Tune/extend as needed.
STRATA = [
    ("computational-biology", 'ISSN:"1553-7358" AND PUB_YEAR:[2018 TO 2022] AND github'),          # PLOS Comput Biol
    ("bioinformatics-methods", 'ISSN:"1471-2105" AND PUB_YEAR:[2018 TO 2022] AND github'),          # BMC Bioinformatics
    ("genomics", 'ISSN:"2047-217X" AND PUB_YEAR:[2018 TO 2022] AND github'),                        # GigaScience
    ("cheminformatics", 'ISSN:"1758-2946" AND PUB_YEAR:[2018 TO 2022] AND github'),                 # J. Cheminformatics
    ("ecology-evolution-methods", 'ISSN:"2041-210X" AND PUB_YEAR:[2018 TO 2022] AND github'),       # Methods Ecol. Evol.
    ("neuroinformatics", 'ISSN:"1539-2791" AND PUB_YEAR:[2018 TO 2022] AND github'),                # Neuroinformatics
]
# Phase-2 strata (need a non-EPMC source — implement a Crossref enumerator, then add here):
#   ("scientific-software", 'ISSN:"2475-9066" ...'),   # JOSS  — repo-guaranteed
#   ("scientific-software", 'ISSN:"2352-7110" ...'),   # SoftwareX — repo-guaranteed
#   ("machine-learning", ...), ("astronomy", ...), ("chemistry", ...)


def enumerate_epmc(query: str, max_papers: int = 2000) -> list[dict]:
    cursor, out = "*", []
    while len(out) < max_papers:
        url = (f"{EPMC}/search?query={urllib.parse.quote(query)}&resultType=core"
               f"&format=json&pageSize=100&cursorMark={urllib.parse.quote(cursor)}")
        data = json.loads(_get(url))
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
    return out


def sample_stratum(domain: str, query: str, n: int, seed: int, seen: set) -> tuple[list, list]:
    pop = enumerate_epmc(query)
    random.Random(seed).shuffle(pop)
    included, excluded = [], []
    for rec in pop:
        if len(included) >= n:
            break
        slug = extract_repo(paper_text(rec))
        if not slug:
            excluded.append({**rec, "reason": "no github repo extracted"}); continue
        if slug.lower() in seen:
            excluded.append({**rec, "repo": slug, "reason": "duplicate repo"}); continue
        seen.add(slug.lower())
        if not repo_public(slug):
            excluded.append({**rec, "repo": slug, "reason": "repo not public/does not exist"}); continue
        included.append({"repo_url": f"https://github.com/{slug}", "domain": domain,
                         "title": rec["title"], "year": rec["year"], "doi": rec.get("doi"), "id": rec["id"]})
        print(f"  [{domain:26}] {slug:40} {rec['title'][:44]}", file=sys.stderr, flush=True)
        time.sleep(0.2)
    return included, excluded


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="cross-domain decay frame (stratified, seeded)")
    ap.add_argument("--per-stratum", type=int, default=15)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="benchmark/frame_crossdomain.json")
    args = ap.parse_args(argv)

    seen, sample, excluded = set(), [], []
    for domain, query in STRATA:
        print(f"enumerating {domain}…", file=sys.stderr, flush=True)
        inc, exc = sample_stratum(domain, query, args.per_stratum, args.seed, seen)
        sample += inc
        excluded += exc

    out = {
        "frame": "cross-domain (Europe PMC strata; phase 1 = computational life-science subfields)",
        "seed": args.seed, "per_stratum": args.per_stratum,
        "strata": [d for d, _ in STRATA], "n": len(sample),
        "sample": sample, "excluded": excluded,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    by_domain = {d: sum(1 for s in sample if s["domain"] == d) for d, _ in STRATA}
    print(f"\nwrote {args.out}: {len(sample)} sampled across {len(STRATA)} strata → {by_domain}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
