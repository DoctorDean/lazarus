#!/usr/bin/env python3
"""Mine a FRESH held-out test-split candidate pool (P3).

``mine_tasks.py`` mines the *contaminated* corpus — the 67 repos already attempted — into
the public **dev** split. This tool does the opposite job. It takes the disjoint
``frame_scaled_new.json`` draw (JOSS + EPMC, "new repos only") and turns it into a review
manifest for the **held-out test split**, whose repos must be ones the project has never
touched (SCOPE §2.2: a test repo whose answer an agent can ``docker pull`` is worthless).

Same discipline as ``mine_tasks.py``: it does only the *mechanical* half — drop anything
contaminated, resolve a domain and language, optionally pin to a pre-Lazarus commit, and
score how gradable each candidate looks — and writes a manifest for a human to vet. **It
never emits a task.** Ground truth is hand-built per task (SCOPE §2.4).

Two axes it scores, both heuristic, both only to *order the human's queue*:

  domain          which of the four prioritised fields the repo sits in. Scope is
                  cross-domain; these just steer where the vetting starts.
  verifiability   how the task would most likely be graded —
                    self-verifying  score recomputed from the input, no answer key
                                    (SCOPE §9's top pattern; should dominate the split)
                    constructible   label rebuildable from a primary source, held off-repo
                    unclear         no obvious computable criterion — probably not a task

Neither score is trusted: a keyword heuristic cannot know a repo admits a residual. It
sorts the queue so the strongest patterns are looked at first, exactly as ``mine_tasks``'s
trust classes do. The decay screen (``lazarus decay-check``, agent-free, ~3 min/repo) and
the hand-built criterion come *after* this, per candidate.

    python benchmark/mine_test_candidates.py                    # offline: classify + stratify
    python benchmark/mine_test_candidates.py --pin --limit 200  # top up SHA pins (GitHub API)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

# Lazarus work started 2026-07-07; pin strictly before it so no task can be solved by a fix
# we ourselves contributed upstream (matches mine_tasks.DEFAULT_CUTOFF).
DEFAULT_CUTOFF = "2026-07-01T00:00:00Z"

FRESH = Path("benchmark/frame_scaled_new.json")            # the disjoint JOSS+EPMC draw
JOSS_FRAMES = (Path("benchmark/frame_joss_scaled.json"),   # carry tags/languages/title
               Path("benchmark/frame_joss.json"))
CONTAM = Path("benchmark/tasks/pins.json")                 # the attempted corpus (70 repos)
TEST_PINS = Path("benchmark/tasks/test_pins.json")         # SHA cache for this pool
DEFAULT_OUT = Path("benchmark/tasks/TEST_CANDIDATES.md")

# Registry tools recovered from *non-git* sources, so they never appear in a frame draw and
# pins.json cannot exclude them — but their answer is a `docker pull` all the same (SCOPE
# §2.2). Belt-and-braces on top of the pins.json exclusion.
REGISTRY_EXTRA = (
    "https://github.com/LPDI-EPFL/masif",      # MaSIF — we PR'd it; flagship revival
    "https://github.com/davek44/Basset",       # Basset — recovered from a 2016 Docker image
    "https://github.com/Discngine/fpocket",    # fpocket — 2010 SourceForge tarball
)

# The four prioritised fields (Dean, P3 kickoff). Scope stays cross-domain; this is only a
# starting order for vetting. Checked most-specific first so a bio/chem signal wins before
# the broad physical/numerical catch-all.
D_STRUCT = "structural/molecular biology"
D_CHEM = "chemistry/materials"
D_GENOMICS = "genomics/bioinformatics"
D_PHYSICAL = "physical/numerical"
D_OTHER = "other"
DOMAIN_ORDER = (D_STRUCT, D_CHEM, D_GENOMICS, D_PHYSICAL, D_OTHER)

_DOMAIN_KW = {
    D_STRUCT: ("protein structure", "structural biology", "docking", "molecular dynamics",
               "crystallograph", "cryo-em", "cryoem", "binding site", "macromolecul",
               "pdb", "ligand", "folding", "structural bioinformatics"),
    D_CHEM: ("cheminformatics", "chemistry", "chemical", "thermodynamic", "equation of state",
             "saft", "materials", "dft", "density functional", "spectroscopy", "spectra",
             "retrosynth", "reaction", "smiles", "qsar", "force field", "quantum chemistry",
             "molecular property"),
    D_GENOMICS: ("genomic", "genome", "sequencing", "rna-seq", "rna seq", "transcriptom",
                 "variant", "snp", "gwas", "phylogen", "metagenom", "single-cell",
                 "single cell", "alignment", "ngs", "read mapping", "assembly", "epigenom",
                 "bioinformatics", "motif", "gene expression", "microbiome"),
    D_PHYSICAL: ("numerical", "linear algebra", "eigen", "matrix", "optimization",
                 "optimisation", "differential equation", "finite element",
                 "finite difference", "integrator", "quadrature", "astronomy",
                 "astrophysics", "cosmology", "physics", "signal", "fourier", "spectral",
                 "time series", "bayesian", "inference", "machine learning", "deep learning",
                 "neural network", "regression", "geospatial", "remote sensing", "hydrology",
                 "plasma", "fluid", "mechanics", "statistics", "dynamical", "simulation"),
}

SELF_VERIFYING = "self-verifying"
CONSTRUCTIBLE = "constructible"
UNCLEAR = "unclear"
VERIFIABILITY_ORDER = (SELF_VERIFYING, CONSTRUCTIBLE, UNCLEAR)

# A criterion recomputable from the input alone (residual, energy, feasibility, round-trip).
_SELF_KW = ("solver", "linear algebra", "eigen", "matrix", "optimization", "optimisation",
            "minimiz", "differential equation", "finite element", "finite difference",
            "integrator", "integration", "quadrature", "root-find", "root find", "newton",
            "simulation", "molecular dynamics", "thermodynamic", "equation of state", "saft",
            "monte carlo", "fourier", "fft", "spectral", "signal", "interpolat",
            "least squares", "curve fit", "symbolic regression", "conservation", "numerical",
            "force field", "dft", "density functional", "quadrature", "sampling")
# A label rebuildable from a primary source (a structure, a deposited dataset, a gold set).
_CONSTRUCT_KW = ("docking", "structure prediction", "interface", "binding", "pose",
                 "alignment", "variant calling", "classif", "segmentation", "phylogen",
                 "contact map", "secondary structure", "motif", "annotation", "detection")


def normalize(url: str) -> str:
    """Canonical repo key for dedup and contamination matching: lower host, no .git/slash."""
    u = (url or "").strip().rstrip("/")
    if u.endswith(".git"):
        u = u[:-4]
    # github.com/Owner/Repo — host is case-insensitive, the path is not, but the corpora are
    # consistent about case so a plain lower() on the whole string is safe and matches how
    # pins.json and the frames store them.
    return u.lower()


def load_fresh(path: Path = FRESH) -> list:
    """The disjoint draw: [{repo_url, arm}, ...], de-duplicated, order preserved."""
    data = json.loads(Path(path).read_text())
    seen, out = set(), []
    for row in data.get("sample") or []:
        u = row.get("repo_url")
        if not u:
            continue
        k = normalize(u)
        if k in seen:
            continue
        seen.add(k)
        out.append({"repo_url": u, "arm": row.get("arm") or ""})
    return out


def load_joss_meta(paths=JOSS_FRAMES) -> dict:
    """norm_url -> {tags, languages, title, year, doi} from whichever JOSS frames exist."""
    meta: dict = {}
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        for row in json.loads(p.read_text()).get("sample") or []:
            u = row.get("repo_url")
            if not u:
                continue
            meta.setdefault(normalize(u), {
                "tags": row.get("tags") or [],
                "languages": row.get("languages") or [],
                "title": row.get("title") or "",
                "year": row.get("year"),
                "doi": row.get("doi") or "",
            })
    return meta


def contaminated_set(pins_path: Path = CONTAM, extra=REGISTRY_EXTRA) -> set:
    """Every repo the project has touched — the attempted corpus plus non-git registry tools."""
    pins = json.loads(Path(pins_path).read_text()) if Path(pins_path).exists() else {}
    return {normalize(u) for u in pins} | {normalize(u) for u in extra}


def _hay(tags, title) -> str:
    return (" ".join(tags) + " " + (title or "")).lower()


def classify_domain(tags, title, arm: str = "") -> str:
    """Best-guess field. EPMC is biomedical by construction, so an unmatched EPMC repo is
    genomics/bioinformatics rather than 'other'."""
    hay = _hay(tags, title)
    for domain in DOMAIN_ORDER:
        if domain == D_OTHER:
            break
        if any(kw in hay for kw in _DOMAIN_KW[domain]):
            return domain
    if (arm or "").upper() == "EPMC":
        return D_GENOMICS
    return D_OTHER


def classify_verifiability(tags, title) -> str:
    """Heuristic grading pattern. self-verifying wins ties — it is the pattern worth the
    most (SCOPE §9), so surface it first even when a constructible keyword also matches."""
    hay = _hay(tags, title)
    if any(kw in hay for kw in _SELF_KW):
        return SELF_VERIFYING
    if any(kw in hay for kw in _CONSTRUCT_KW):
        return CONSTRUCTIBLE
    return UNCLEAR


def slug_of(repo_url: str) -> str:
    return repo_url.rstrip("/").split("github.com/")[-1].removesuffix(".git")


def build_rows(fresh: list, joss_meta: dict, contaminated: set) -> tuple:
    """Enrich, drop contaminated, classify. Returns (rows, stats). Pure — no network."""
    rows, excluded = [], 0
    for cand in fresh:
        key = normalize(cand["repo_url"])
        if key in contaminated:
            excluded += 1
            continue
        m = joss_meta.get(key, {})
        tags, title = m.get("tags", []), m.get("title", "")
        langs = m.get("languages", [])
        domain = classify_domain(tags, title, cand["arm"])
        verif = classify_verifiability(tags, title)
        rows.append({
            "repo_url": cand["repo_url"],
            "slug": slug_of(cand["repo_url"]),
            "arm": cand["arm"],
            "domain": domain,
            "verifiability": verif,
            "languages": langs,
            "tags": tags,
            "title": title,
            "year": m.get("year"),
            "sha": None,
            "date": None,
        })

    def _sort_key(r):
        return (DOMAIN_ORDER.index(r["domain"]),
                VERIFIABILITY_ORDER.index(r["verifiability"]),
                r["slug"].lower())

    rows.sort(key=_sort_key)
    stats = {
        "fresh_total": len(fresh),
        "excluded_contaminated": excluded,
        "candidates": len(rows),
        "by_arm": _tally(rows, "arm"),
        "by_domain": _tally(rows, "domain"),
        "by_verifiability": _tally(rows, "verifiability"),
        "matrix": _matrix(rows),
    }
    return rows, stats


def _tally(rows, field) -> dict:
    out: dict = {}
    for r in rows:
        out[r[field] or "—"] = out.get(r[field] or "—", 0) + 1
    return out


def _matrix(rows) -> dict:
    """domain -> {verifiability -> count}, over the four target domains + other."""
    mat = {d: {v: 0 for v in VERIFIABILITY_ORDER} for d in DOMAIN_ORDER}
    for r in rows:
        mat[r["domain"]][r["verifiability"]] += 1
    return mat


def render_markdown(rows: list, stats: dict, cutoff: str) -> str:
    pinned = sum(1 for r in rows if r["sha"])
    L = [
        "# Test-split candidates — needs review",
        "",
        "Generated by `python benchmark/mine_test_candidates.py`. **These are not tasks.**",
        "This is the *fresh* pool for the held-out **test** split: repos the project has",
        "never attempted (disjoint from `tasks/pins.json`). Each row still needs a human to",
        "(1) confirm it is dead today (`lazarus decay-check`), (2) define a harness-owned",
        "criterion — self-verifying wherever possible (SCOPE §9) — and (3) confirm the task",
        "is *achievable* before it is frozen. See `../LEADERBOARD_SCOPE.md` §2.2, §9.",
        "",
        f"- **{stats['candidates']}** fresh candidates "
        f"({stats['excluded_contaminated']} dropped as contaminated, "
        f"{stats['fresh_total']} in the draw), {pinned} pinned before `{cutoff}`",
        f"- target: a **50-task** test split, self-verifying core + constructible tail",
        "",
        "### Verifiability (how it would be graded)",
        f"- `{SELF_VERIFYING}`: {stats['by_verifiability'].get(SELF_VERIFYING, 0)} — "
        "graded by recomputation from the input; no answer key. **Prefer these.**",
        f"- `{CONSTRUCTIBLE}`: {stats['by_verifiability'].get(CONSTRUCTIBLE, 0)} — "
        "label rebuildable from a primary source, held off-repo.",
        f"- `{UNCLEAR}`: {stats['by_verifiability'].get(UNCLEAR, 0)} — "
        "no obvious computable criterion (many are viz / IO / data-management; likely not tasks).",
        "",
        "### Stratification — domain × verifiability",
        "",
        "| domain | self-verifying | constructible | unclear | total |",
        "|---|--:|--:|--:|--:|",
    ]
    for d in DOMAIN_ORDER:
        m = stats["matrix"][d]
        tot = sum(m.values())
        if tot == 0:
            continue
        L.append(f"| {d} | {m[SELF_VERIFYING]} | {m[CONSTRUCTIBLE]} | {m[UNCLEAR]} | {tot} |")
    L.append("")
    L.append("Note: EPMC-arm repos carry no JOSS tags, so they classify weakly (mostly")
    L.append("`unclear` in genomics/bioinformatics) and need hands-on review. The JOSS arm is")
    L.append("where the cross-domain self-verifying candidates concentrate.")
    L.append("")

    # Per-domain detail for the four target fields; 'other' is summarised, not detailed.
    for d in DOMAIN_ORDER:
        drows = [r for r in rows if r["domain"] == d]
        if not drows:
            continue
        if d == D_OTHER:
            L.append(f"## {d} ({len(drows)}) — out of the prioritised scope, listed for completeness")
            L.append("")
            L.append(", ".join(f"[{r['slug']}]({r['repo_url']})" for r in drows))
            L.append("")
            continue
        L.append(f"## {d} ({len(drows)})")
        L.append("")
        L.append("| verifiability | repo | arm | lang | tags | pin |")
        L.append("|---|---|---|---|---|---|")
        for r in drows:
            tags = ", ".join(r["tags"][:3]) or "—"
            lang = "/".join(r["languages"][:2]) or "—"
            pin = (r["sha"] or "")[:8] or "—"
            L.append(f"| `{r['verifiability']}` | [{r['slug']}]({r['repo_url']}) | "
                     f"{r['arm'] or '—'} | {lang} | {tags} | `{pin}` |")
        L.append("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="mine fresh held-out test-split candidates")
    ap.add_argument("--fresh", default=str(FRESH))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    ap.add_argument("--pin", action="store_true",
                    help="resolve pre-cutoff SHAs via the GitHub API (network; cached)")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap API lookups this run (GitHub rate limit); 0 = no cap")
    ap.add_argument("--domain", choices=DOMAIN_ORDER, help="only pin candidates in this domain")
    ap.add_argument("--verifiability", choices=VERIFIABILITY_ORDER,
                    help="only pin candidates of this verifiability class (e.g. self-verifying)")
    args = ap.parse_args(argv)

    fresh = load_fresh(Path(args.fresh))
    joss_meta = load_joss_meta()
    contaminated = contaminated_set()
    rows, stats = build_rows(fresh, joss_meta, contaminated)

    if args.pin:
        import mine_tasks  # reuse the one GitHub access path (token, _api, cache resume)
        cache = json.loads(TEST_PINS.read_text()) if TEST_PINS.exists() else {}
        print(f"github auth: {'token (5000/hr)' if mine_tasks._token() else 'anonymous (60/hr)'}")
        looked_up = 0
        for r in rows:
            if args.domain and r["domain"] != args.domain:
                continue
            if args.verifiability and r["verifiability"] != args.verifiability:
                continue
            was_cached = r["repo_url"] in cache
            if not was_cached and args.limit and looked_up >= args.limit:
                continue
            sha, date = mine_tasks.pin_commit(r["repo_url"], args.cutoff, cache)
            r["sha"], r["date"] = sha, date
            looked_up += 0 if was_cached else 1
        TEST_PINS.parent.mkdir(parents=True, exist_ok=True)
        TEST_PINS.write_text(json.dumps(cache, indent=2, sort_keys=True))
        # reflect any newly-cached pins onto every row
        for r in rows:
            if r["repo_url"] in cache and not r["sha"]:
                r["sha"] = cache[r["repo_url"]].get("sha")
                r["date"] = cache[r["repo_url"]].get("date")
        print(f"pinned this run: {looked_up} API lookups")

    Path(args.out).write_text(render_markdown(rows, stats, args.cutoff))
    print(f"{stats['candidates']} candidates "
          f"({stats['excluded_contaminated']} contaminated dropped) -> {args.out}")
    for d in DOMAIN_ORDER:
        m = stats["matrix"][d]
        tot = sum(m.values())
        if tot:
            print(f"  {d:<30} self={m[SELF_VERIFYING]:<3} "
                  f"constr={m[CONSTRUCTIBLE]:<3} unclear={m[UNCLEAR]:<3} total={tot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
