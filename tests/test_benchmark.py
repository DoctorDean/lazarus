"""Tests for the benchmark harness — the pure pieces (classify, results IO,
summarize, provisional_entry). The live `run_one` needs Docker + auth."""
import json
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


def test_force_remove_retries_and_handles_flaky_kill():
    class _CR:
        def __init__(self, ok, stderr=""):
            self.ok, self.stderr = ok, stderr
    class _Client:
        def __init__(self, results):
            self.results, self.calls = list(results), 0
        def run(self, args, **kw):
            self.calls += 1
            r = self.results[min(self.calls - 1, len(self.results) - 1)]
            if isinstance(r, Exception):
                raise r
            return r
    # transient failures (non-ok rm) then success → keeps retrying, returns True
    c = _Client([_CR(False), _CR(False), _CR(True)])
    assert run._force_remove(c, "box", budget_s=1.0, poll=0) is True and c.calls == 3
    # a hung kill (raises) then success → the swallow-and-retry path still wins
    c = _Client([RuntimeError("ssh timeout"), _CR(True)])
    assert run._force_remove(c, "box", budget_s=1.0, poll=0) is True
    # "No such container" = already gone → success on the first attempt
    c = _Client([_CR(False, stderr="Error: No such container: box")])
    assert run._force_remove(c, "box", budget_s=1.0, poll=0) is True and c.calls == 1
    # never succeeds → gives up at the budget (no infinite loop)
    c = _Client([_CR(False)])
    assert run._force_remove(c, "box", budget_s=0.05, poll=0) is False
    # run finished on its own (stop() True) → bail before issuing any rm
    c = _Client([_CR(True)])
    assert run._force_remove(c, "box", budget_s=1.0, poll=0, stop=lambda: True) is False and c.calls == 0


def test_collect_urls_merges_sources_and_dedups(tmp_path):
    repos = tmp_path / "repos.txt"
    repos.write_text("https://github.com/o/a  # keep\n\n# comment only\nhttps://github.com/o/b\n")
    frame = tmp_path / "frame.json"
    frame.write_text(json.dumps({"sample": [
        {"repo_url": "https://github.com/o/b"},   # dup of a --repos entry
        {"repo_url": "https://github.com/o/c"},
    ]}))
    urls = run.collect_urls(["https://github.com/o/a"], str(repos), str(frame))
    # order preserved (url, then repos, then frame), inline # comments stripped, dups removed
    assert urls == ["https://github.com/o/a", "https://github.com/o/b", "https://github.com/o/c"]
    assert run.collect_urls() == []


def test_summarize_rates_and_reasons():
    rows = [
        {"repo_url": "a", "outcome": "reproduced", "naive_runs": False},
        {"repo_url": "b", "outcome": "revived", "naive_runs": False},
        {"repo_url": "c", "outcome": "weights-gone", "naive_runs": False},
        {"repo_url": "d", "outcome": "revived", "naive_runs": True},   # ran on its own → not "dead"
        {"repo_url": "e", "outcome": "infra-failed", "naive_runs": False},  # excluded from the rate
    ]
    s = report.summarize(rows)
    assert s["attempted"] == 4 and s["infra_failed"] == 1              # infra excluded from attempted
    assert s["revived"] == 3 and s["reproduced"] == 1
    # 3 dead (a,b,c); 2 of them revived → 67%  (infra 'e' not counted as dead)
    assert round(s["revival_rate"], 2) == 0.67
    assert round(s["decay_rate"], 2) == 0.75
    assert s["reasons"]["revived"] == 2
    assert "reproduced" in report.render(rows)


def test_wilson_ci_and_baseline_merge():
    # Wilson interval: bounded to [0,1], brackets the point estimate, and a known value.
    assert report.wilson_ci(0, 0) is None
    lo, hi = report.wilson_ci(17, 20)          # 85% decay of 20
    assert 0 <= lo < 0.85 < hi <= 1
    assert round(lo, 2) == 0.64 and round(hi, 2) == 0.95   # standard Wilson 95% for 17/20
    lo, hi = report.wilson_ci(20, 20)          # all successes: upper bound stays <1, lower <1
    assert hi == 1.0 and lo < 1.0
    # merge_baseline fills naive_runs from the baseline file by repo_url, leaves others
    rows = [{"repo_url": "a", "outcome": "revived", "naive_runs": None},
            {"repo_url": "b", "outcome": "revived", "naive_runs": True}]
    base = [{"repo_url": "a", "naive_runs": False}]
    merged = report.merge_baseline(rows, base)
    assert merged[0]["naive_runs"] is False        # filled from baseline
    assert merged[1]["naive_runs"] is True         # untouched (already set)
    assert rows[0]["naive_runs"] is None           # original not mutated
    # CIs now surface in the summary + render
    s = report.summarize(merged)
    assert s["decay_ci"] is not None and s["revival_ci"] is not None
    assert "95% CI" in report.render(merged)


def test_frame_extract_repo():
    import frame  # noqa: E402  (benchmark/ is on sys.path)
    t = ("Availability: implemented in Python, freely available at "
         "https://github.com/My-Lab/CoolTool.git; issues at github.com/My-Lab/CoolTool/issues")
    assert frame.extract_repo(t) == "My-Lab/CoolTool"           # strips .git and /issues
    assert frame.extract_repo("see github.com/features/actions for CI") is None  # bad owner
    assert frame.extract_repo("no code here") is None


def test_baseline_language_and_image():
    import baseline  # noqa: E402
    assert baseline.primary_language({"Python": 9000, "Shell": 100}) == "python"
    assert baseline.primary_language({"R": 5000, "C++": 200}) == "r"
    assert baseline.primary_language({"Jupyter Notebook": 800}) == "python"
    assert baseline.primary_language({}) == "python"
    assert "rocker" in baseline.base_image_for("r")
    assert "miniconda" in baseline.base_image_for("python")
    # README extractor: skip install blocks, return the first real usage block's code
    md = ("# Tool\n## Install\n```bash\npip install tool\n```\n"
          "## Usage\n```python\nfrom tool import run\nrun('x')\n```\n")
    code = baseline.readme_example(md)
    assert "run('x')" in code and "pip install" not in code
    # a real R usage line survives even next to a trivial library() line
    assert "simpg()" in baseline.readme_example("```r\nlibrary(simurg)\npg <- simpg()\n```")
    # help-only / install-only / no-code blocks are not runnable examples
    assert baseline.readme_example("```r\nhelp('simpg')\n```") is None
    assert baseline.readme_example("```r\ninstall_github('a/b')\n```") is None
    assert baseline.readme_example("no code blocks here") is None
    # the protocol embeds a machine-readable verdict line the runner parses
    assert "===BASELINE===" in baseline.PROTOCOL and "REPO_URL" in baseline.PROTOCOL


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
