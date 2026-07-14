"""Tests for the benchmark harness — the pure pieces (classify, results IO,
summarize, provisional_entry). The live `run_one` needs Docker + auth."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmark"))

import run  # noqa: E402
import report  # noqa: E402


def _c(**kw):
    base = dict(completed=True, is_error=False, contract_emitted=True, reproduced=False,
                revived=True, timed_out=False, hit_turn_cap=False, final_text="")
    base.update(kw)
    return run.classify(**base)


def test_classify_success_tiers():
    assert _c(reproduced=True) == "reproduced"
    assert _c(reproduced=False, revived=True) == "revived"
    assert _c(reproduced=False, revived=False) == "runs-unverified"


def test_classify_budget_and_failures():
    fail = dict(completed=False, is_error=True, contract_emitted=False, reproduced=False, revived=False)
    assert run.classify(**fail, timed_out=True, hit_turn_cap=False) == "budget-exceeded"
    assert run.classify(**fail, timed_out=False, hit_turn_cap=True) == "budget-exceeded"
    assert run.classify(**fail, timed_out=False, hit_turn_cap=False,
                        final_text="the pretrained weights URL returns 404, no longer available") == "weights-gone"
    assert run.classify(**fail, timed_out=False, hit_turn_cap=False,
                        final_text="binary aborts with SIGILL / illegal instruction under emulation") == "hardware-incompatible"
    assert run.classify(**fail, timed_out=False, hit_turn_cap=False,
                        final_text="the dataset requires registration and credential access") == "data-gated"
    assert run.classify(**fail, timed_out=False, hit_turn_cap=False,
                        final_text="something else entirely broke") == "unresolvable-deps"


def test_reproduced_uses_harness_tolerance_not_agents():
    # the shakedown bug: an agent set tolerance=10 so 18-vs-14.1 self-awarded "reproduced"
    assert run.reproduced_ok(0.8993, 0.88) is True     # 2% — genuinely close
    assert run.reproduced_ok(18.0, 14.1) is False      # 28% — not a reproduction
    assert run.reproduced_ok(0.90, 0.88) is True
    assert run.reproduced_ok(None, 0.88) is False
    assert run.reproduced_ok(0.5, 0) is False


def test_interpret_smoke_verdicts_and_metrics():
    assert run.interpret_smoke("...\nPASS\n") is True
    assert run.interpret_smoke("Traceback...\nFAIL") is False
    assert run.interpret_smoke("roc_auc=0.91 done", "roc_auc", 0.8) is True     # higher-is-better
    assert run.interpret_smoke("rmsd = 1.20 A", "rmsd", 2.0) is True            # lower-is-better, passes
    assert run.interpret_smoke("rmsd: 3.5", "rmsd", 2.0) is False               # lower-is-better, fails
    assert run.interpret_smoke("just some logs, no verdict") is None
    # the pilot bug: a non-TTY docker warning contains "failed" — must NOT read as a verdict
    noise = "pearson_r=1.000000\nmesg: ttyname failed: Inappropriate ioctl for device"
    assert run.interpret_smoke(noise, "pearson_r", 0.9) is True


def test_results_io_roundtrip(tmp_path):
    p = tmp_path / "results.json"
    rows = [run.BenchmarkResult(repo_url="u/a", outcome="revived").to_dict()]
    run.save_results(str(p), rows)
    back = run.load_results(str(p))
    assert back == rows
    assert run.already_done(back, "u/a") and not run.already_done(back, "u/b")


def test_summarize_rates_and_reasons():
    rows = [
        {"repo_url": "a", "outcome": "reproduced", "naive_runs": False},
        {"repo_url": "b", "outcome": "revived", "naive_runs": False},
        {"repo_url": "c", "outcome": "weights-gone", "naive_runs": False},
        {"repo_url": "d", "outcome": "revived", "naive_runs": True},   # ran on its own → not "dead"
    ]
    s = report.summarize(rows)
    assert s["attempted"] == 4 and s["revived"] == 3 and s["reproduced"] == 1
    # 3 dead (a,b,c); 2 of them revived → 67%
    assert round(s["revival_rate"], 2) == 0.67
    assert round(s["decay_rate"], 2) == 0.75   # 3 of 4 didn't run on their own
    assert s["reasons"]["revived"] == 2
    assert "reproduced" in report.render(rows)


def test_provisional_entry_from_contract():
    from lazarus.contract import Contract, SmokeCheck, Benchmark

    class _Plan:
        capability = "dock a ligand into a protein"
        needs_gpu = True
    c = Contract(name="foo_predict", repo_url="https://github.com/x/foo", base_image="lazarus/foo:ok",
                 entrypoint="", smoke=SmokeCheck(description="d", command="c", metric="rmsd", threshold=2.0),
                 benchmark=Benchmark(description="d", metric="rate", reported=0.4, measured=0.38), gpus="all")
    res = run.BenchmarkResult(repo_url="https://github.com/x/foo", turns=42, notes="benchmark/output/foo")
    e = run.provisional_entry(c, _Plan(), res, added="2026-07-11")
    assert e.name == "foo_predict" and e.gpu is True and e.from_url is True
    assert e.sanity_metric == "rmsd" and e.reproduced_measured == 0.38
    assert e.domain == "" and e.era == ""   # left blank => 'needs curation'
