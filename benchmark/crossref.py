#!/usr/bin/env python3
"""Crossref sourcing for the cross-domain decay frame (Track 2).

Europe PMC is biomedical, so it can't reach the venues that make the sample genuinely
*cross-domain*. Crossref indexes every DOI across all fields, so it's the right source for
JOSS (ISSN 2475-9066), SoftwareX (2352-7110), and any domain journal by ISSN.

This module enumerates works by ISSN and tries to extract a public GitHub repo from the
metadata Crossref actually carries (abstract JATS + link/resource URLs). Yield varies by
venue — run the probe below to measure it before committing compute:

    python benchmark/crossref.py --issn 2475-9066 --issn 2352-7110 --cap 60

Pure stdlib; polite HTTP to api.crossref.org + github.com. No API key. Reuses the GitHub
regex + public-repo screen from frame.py so extraction is identical to the Track-1 frame.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame import GH_RE, BAD_OWNERS, BAD_REPOS, repo_public  # noqa: E402

CROSSREF = "https://api.crossref.org/works"
# Crossref etiquette: identify the tool (no personal email committed to the repo).
UA = {"User-Agent": "lazarus-benchmark/0.3 (research-code decay study; +https://github.com/DoctorDean/lazarus)"}


def _get(url: str, timeout: float = 40) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as fh:  # noqa: S310
        return fh.read()


def enumerate_by_issn(issn: str, cap: int = 200) -> list[dict]:
    """Works for one ISSN, newest first, paged via Crossref's deep-paging cursor."""
    cursor, out = "*", []
    select = "DOI,title,container-title,abstract,link,resource,issued,subject"
    while len(out) < cap:
        url = (f"{CROSSREF}?filter=issn:{issn}&rows=100&select={select}"
               f"&cursor={urllib.parse.quote(cursor)}")
        msg = json.loads(_get(url)).get("message", {})
        items = msg.get("items", [])
        if not items:
            break
        out.extend(items)
        cursor = msg.get("next-cursor")
        if not cursor:
            break
        time.sleep(0.3)
    return out[:cap]


def _candidate_text(rec: dict) -> str:
    """All the places a repo URL might hide in Crossref metadata."""
    parts = [rec.get("abstract", "") or ""]
    for lk in rec.get("link", []) or []:
        parts.append(lk.get("URL", "") or "")
    res = (rec.get("resource", {}) or {}).get("primary", {}) or {}
    parts.append(res.get("URL", "") or "")
    return "\n".join(parts)


def extract_repo(rec: dict) -> str | None:
    """Best public github owner/repo from a Crossref record, or None."""
    from collections import Counter
    cands = []
    for owner, repo in GH_RE.findall(_candidate_text(rec)):
        repo = repo.rstrip(".").removesuffix(".git")
        if owner.lower() in BAD_OWNERS or not repo or repo.lower() in BAD_REPOS:
            continue
        cands.append(f"{owner}/{repo}")
    return Counter(cands).most_common(1)[0][0] if cands else None


def _year(rec: dict) -> int | None:
    try:
        return (rec.get("issued", {}).get("date-parts", [[None]])[0] or [None])[0]
    except Exception:  # noqa: BLE001
        return None


def probe(issns: list[str], cap: int) -> None:
    """Report, per ISSN: total records fetched, how many carry an extractable repo, and samples."""
    print(f"{'issn':12} {'venue':26} {'fetched':>7} {'w/repo':>6} {'yield':>6}  samples")
    for issn in issns:
        recs = enumerate_by_issn(issn, cap)
        venue = (recs[0].get("container-title", ["?"]) or ["?"])[0][:24] if recs else "?"
        repos = [extract_repo(r) for r in recs]
        hits = [s for s in repos if s]
        y = f"{100*len(hits)/max(1,len(recs)):.0f}%"
        print(f"{issn:12} {venue:26} {len(recs):>7} {len(hits):>6} {y:>6}  {hits[:3]}")
        time.sleep(0.3)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="probe Crossref repo-extraction yield by ISSN")
    ap.add_argument("--issn", action="append", required=True, help="ISSN (repeatable)")
    ap.add_argument("--cap", type=int, default=60, help="records to fetch per ISSN")
    args = ap.parse_args(argv)
    probe(args.issn, args.cap)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
