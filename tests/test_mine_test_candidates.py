"""Tests for the P3 fresh test-candidate miner — the pure pieces (normalize, contamination
exclusion, domain/verifiability classification, stratification, manifest rendering). The
``--pin`` path needs the GitHub API and is not exercised here."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmark"))

import mine_test_candidates as m  # noqa: E402


def test_normalize_canonicalizes():
    a = m.normalize("https://github.com/Owner/Repo.git")
    b = m.normalize("https://github.com/owner/repo/")
    assert a == b == "https://github.com/owner/repo"


def test_load_fresh_dedups(tmp_path):
    p = tmp_path / "fresh.json"
    p.write_text(json.dumps({"sample": [
        {"repo_url": "https://github.com/a/b", "arm": "JOSS"},
        {"repo_url": "https://github.com/a/b/", "arm": "JOSS"},   # dup after normalize
        {"repo_url": "https://github.com/c/d", "arm": "EPMC"},
        {"arm": "JOSS"},                                          # no url -> skipped
    ]}))
    rows = m.load_fresh(p)
    assert [r["repo_url"] for r in rows] == ["https://github.com/a/b", "https://github.com/c/d"]


def test_contaminated_set_includes_pins_and_registry(tmp_path):
    pins = tmp_path / "pins.json"
    pins.write_text(json.dumps({"https://github.com/some/attempted": {"sha": "abc"}}))
    contam = m.contaminated_set(pins_path=pins)
    assert "https://github.com/some/attempted" in contam
    # the non-git registry tools ride along even though no frame draw would contain them
    assert m.normalize(m.REGISTRY_EXTRA[0]) in contam


def test_build_rows_drops_contaminated_keeps_fresh():
    contam = {m.normalize("https://github.com/pyamg/pyamg")}
    fresh = [
        {"repo_url": "https://github.com/pyamg/pyamg", "arm": "JOSS"},     # contaminated
        {"repo_url": "https://github.com/brand/new", "arm": "JOSS"},       # kept
    ]
    rows, stats = m.build_rows(fresh, joss_meta={}, contaminated=contam)
    assert [r["slug"] for r in rows] == ["brand/new"]
    assert stats["excluded_contaminated"] == 1
    assert stats["candidates"] == 1


def test_classify_domain_specific_beats_broad():
    # 'molecular dynamics' is structbio even though 'simulation'/'dynamics' are physical
    assert m.classify_domain(["molecular dynamics"], "") == m.D_STRUCT
    assert m.classify_domain(["thermodynamics", "SAFT"], "") == m.D_CHEM
    assert m.classify_domain(["genomics", "variant"], "") == m.D_GENOMICS
    assert m.classify_domain(["linear algebra", "solver"], "") == m.D_PHYSICAL


def test_classify_domain_epmc_defaults_to_genomics_not_other():
    # an EPMC repo with no JOSS tags is biomedical by construction, not 'other'
    assert m.classify_domain([], "", arm="EPMC") == m.D_GENOMICS
    assert m.classify_domain([], "", arm="JOSS") == m.D_OTHER


def test_classify_verifiability_precedence():
    # self-verifying wins over constructible when both keywords appear (SCOPE §9)
    assert m.classify_verifiability(["linear algebra solver", "docking"], "") == m.SELF_VERIFYING
    assert m.classify_verifiability(["protein docking"], "") == m.CONSTRUCTIBLE
    assert m.classify_verifiability(["visualization", "plotting"], "") == m.UNCLEAR


def test_render_is_a_manifest_never_a_task():
    fresh = [{"repo_url": "https://github.com/x/solver", "arm": "JOSS"}]
    meta = {m.normalize("https://github.com/x/solver"):
            {"tags": ["linear algebra"], "languages": ["Python"], "title": "A solver"}}
    rows, stats = m.build_rows(fresh, meta, contaminated=set())
    md = m.render_markdown(rows, stats, m.DEFAULT_CUTOFF)
    assert "**These are not tasks.**" in md
    assert "domain × verifiability" in md
    # the manifest must not carry anything shaped like an answer key or a task spec
    assert "evaluation:" not in md and "labels" not in md and "threshold" not in md


def test_stratification_matrix_totals_match():
    fresh = [
        {"repo_url": "https://github.com/a/solver", "arm": "JOSS"},
        {"repo_url": "https://github.com/b/dock", "arm": "JOSS"},
        {"repo_url": "https://github.com/c/viz", "arm": "JOSS"},
    ]
    meta = {
        m.normalize("https://github.com/a/solver"): {"tags": ["linear algebra"], "title": ""},
        m.normalize("https://github.com/b/dock"): {"tags": ["protein docking"], "title": ""},
        m.normalize("https://github.com/c/viz"): {"tags": ["visualization"], "title": ""},
    }
    rows, stats = m.build_rows(fresh, meta, contaminated=set())
    grand = sum(sum(v.values()) for v in stats["matrix"].values())
    assert grand == stats["candidates"] == 3


def test_real_pool_is_disjoint_from_attempted():
    """Regression guard: the shipped fresh pool must share nothing with the attempted corpus,
    or a test task could be solved by `docker pull`. Skips if the data isn't present."""
    fresh_p = ROOT / "benchmark" / "frame_scaled_new.json"
    pins_p = ROOT / "benchmark" / "tasks" / "pins.json"
    if not (fresh_p.exists() and pins_p.exists()):
        return
    fresh = {m.normalize(r["repo_url"]) for r in json.loads(fresh_p.read_text())["sample"]
             if r.get("repo_url")}
    contam = m.contaminated_set(pins_path=pins_p)
    assert fresh & contam == set()
