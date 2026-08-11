"""Tests for the leaderboard task layer — specs, evaluators, and grading.

The point of this layer is that the *harness* owns the success criterion, so these
tests lean on the cases where a submission could otherwise cheat or a grader could
quietly lie: unpinned commits, inferred metric directions, shuffled output rows,
missing ids, and ungradable runs being counted as failures.

Offline; synthetic data except the one real end-to-end task.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmark"))

import evaluators  # noqa: E402
import run  # noqa: E402
import score as scoring  # noqa: E402
import task as task_mod  # noqa: E402
from task import Task, TaskError  # noqa: E402

SHA = "a61623cd98d243c2ff4cd03fc3619d2d22ec50e7"


def _spec(**over):
    d = {
        "id": "demo-task",
        "repo_url": "https://github.com/example/dead",
        "commit": SHA,
        "kind": "predict",
        "capability": "predict something",
        "input_path": "input/in.txt",
        "output_path": "prediction.csv",
        "evaluation": {"evaluator": "auroc", "metric": "auroc",
                       "direction": "higher", "threshold": 0.7,
                       "labels": "labels/y.csv"},
    }
    for k, v in over.items():
        if k == "evaluation":
            d["evaluation"] = {**d["evaluation"], **v}
        else:
            d[k] = v
    return d


# --------------------------------------------------------------------------
# spec validation — the contamination and inference guards
# --------------------------------------------------------------------------
def test_task_loads_and_validates():
    t = Task.from_dict(_spec())
    assert t.id == "demo-task" and t.kind == "predict"
    assert t.caps.turns == 90                      # defaults applied


@pytest.mark.parametrize("commit", ["main", "HEAD", "v1.2.0", "", "zzzzzzz"])
def test_task_rejects_an_unpinned_commit(commit):
    """Branches/tags move — including via our own give-back PRs — so they're refused."""
    with pytest.raises(TaskError, match="pinned git SHA"):
        Task.from_dict(_spec(commit=commit))


def test_predict_task_requires_an_explicit_direction():
    """Never infer direction from the metric name; that's what broke interpret_smoke."""
    with pytest.raises(TaskError, match="direction"):
        Task.from_dict(_spec(evaluation={"direction": ""}))
    with pytest.raises(TaskError, match="direction"):
        Task.from_dict(_spec(evaluation={"direction": "up"}))


def test_predict_task_requires_input_labels_and_threshold():
    with pytest.raises(TaskError, match="labels"):
        Task.from_dict(_spec(evaluation={"labels": ""}))
    with pytest.raises(TaskError, match="input_path"):
        Task.from_dict(_spec(input_path=""))
    with pytest.raises(TaskError, match="threshold"):
        Task.from_dict(_spec(evaluation={"threshold": None}))


def test_reproduce_task_requires_the_reported_value():
    ok = Task.from_dict(_spec(kind="reproduce", evaluation={
        "evaluator": "scalar", "metric": "auroc", "reported": 0.9,
        "direction": "", "threshold": None, "labels": ""}))
    assert ok.evaluation.rel_tol == 0.15
    with pytest.raises(TaskError, match="reported"):
        Task.from_dict(_spec(kind="reproduce", evaluation={
            "evaluator": "scalar", "reported": None, "direction": "", "threshold": None}))


def test_task_rejects_unknown_fields_and_bad_enums():
    with pytest.raises(TaskError, match="unknown task field"):
        Task.from_dict(_spec(sneaky="value"))
    with pytest.raises(TaskError, match="kind"):
        Task.from_dict(_spec(kind="freestyle"))
    with pytest.raises(TaskError, match="split"):
        Task.from_dict(_spec(split="secret"))


def test_load_tasks_rejects_duplicate_ids(tmp_path):
    import yaml
    for sub in ("a", "b"):
        d = tmp_path / sub
        d.mkdir()
        (d / "task.yaml").write_text(yaml.safe_dump(_spec()))
    with pytest.raises(TaskError, match="duplicate task id"):
        task_mod.load_tasks(tmp_path)


# --------------------------------------------------------------------------
# evaluators — the submission's output is untrusted input
# --------------------------------------------------------------------------
def _write(p, text):
    p.write_text(text)
    return p


def test_auroc_is_correct_and_order_independent(tmp_path):
    labels = _write(tmp_path / "y.csv", "id,label\na,1\nb,0\nc,1\nd,0\n")
    perfect = _write(tmp_path / "p.csv", "id,score\na,0.9\nb,0.1\nc,0.8\nd,0.2\n")
    assert evaluators.auroc(perfect, labels) == pytest.approx(1.0)
    # same predictions, rows shuffled — must join on id, not position
    shuffled = _write(tmp_path / "s.csv", "id,score\nd,0.2\na,0.9\nc,0.8\nb,0.1\n")
    assert evaluators.auroc(shuffled, labels) == pytest.approx(1.0)
    inverted = _write(tmp_path / "i.csv", "id,score\na,0.1\nb,0.9\nc,0.2\nd,0.8\n")
    assert evaluators.auroc(inverted, labels) == pytest.approx(0.0)


def test_auroc_handles_ties_as_a_coin_flip(tmp_path):
    """A constant-score submission must score 0.5, not an arbitrary value."""
    labels = _write(tmp_path / "y.csv", "id,label\na,1\nb,0\nc,1\nd,0\n")
    flat = _write(tmp_path / "p.csv", "id,score\na,0.5\nb,0.5\nc,0.5\nd,0.5\n")
    assert evaluators.auroc(flat, labels) == pytest.approx(0.5)


def test_auroc_rejects_incomplete_or_malformed_submissions(tmp_path):
    labels = _write(tmp_path / "y.csv", "id,label\na,1\nb,0\nc,1\n")
    short = _write(tmp_path / "p1.csv", "id,score\na,0.9\nb,0.1\n")
    with pytest.raises(evaluators.EvaluationError, match="missing"):
        evaluators.auroc(short, labels)
    dupes = _write(tmp_path / "p2.csv", "id,score\na,0.9\na,0.5\nb,0.1\nc,0.8\n")
    with pytest.raises(evaluators.EvaluationError, match="duplicate"):
        evaluators.auroc(dupes, labels)
    junk = _write(tmp_path / "p3.csv", "id,score\na,high\nb,0.1\nc,0.8\n")
    with pytest.raises(evaluators.EvaluationError, match="not a number"):
        evaluators.auroc(junk, labels)
    nan = _write(tmp_path / "p4.csv", "id,score\na,nan\nb,0.1\nc,0.8\n")
    with pytest.raises(evaluators.EvaluationError, match="finite"):
        evaluators.auroc(nan, labels)
    wrongcols = _write(tmp_path / "p5.csv", "name,value\na,0.9\n")
    with pytest.raises(evaluators.EvaluationError, match="columns"):
        evaluators.auroc(wrongcols, labels)


def test_auroc_needs_both_classes(tmp_path):
    labels = _write(tmp_path / "y.csv", "id,label\na,1\nb,1\n")
    pred = _write(tmp_path / "p.csv", "id,score\na,0.9\nb,0.1\n")
    with pytest.raises(evaluators.EvaluationError, match="both classes"):
        evaluators.auroc(pred, labels)


def test_rmse_and_accuracy(tmp_path):
    labels = _write(tmp_path / "y.csv", "id,label\na,1.0\nb,3.0\n")
    pred = _write(tmp_path / "p.csv", "id,score\na,2.0\nb,4.0\n")
    assert evaluators.rmse(pred, labels) == pytest.approx(1.0)
    lab2 = _write(tmp_path / "y2.csv", "id,label\na,1\nb,0\nc,1\nd,1\n")
    pr2 = _write(tmp_path / "p2.csv", "id,score\na,1\nb,0\nc,0\nd,1\n")
    assert evaluators.accuracy(pr2, lab2) == pytest.approx(0.75)


def test_scalar_prefers_the_labelled_metric_and_refuses_to_guess(tmp_path):
    t = Task.from_dict(_spec(kind="reproduce", evaluation={
        "evaluator": "scalar", "metric": "auroc", "reported": 0.9,
        "direction": "", "threshold": None, "labels": ""}))
    ok = _write(tmp_path / "a.txt", "training done in 45 epochs\nauroc=0.8944\n")
    assert evaluators.scalar(ok, None, t) == pytest.approx(0.8944)
    # several bare numbers and no labelled metric -> refuse rather than pick one
    ambiguous = _write(tmp_path / "b.txt", "45 epochs, loss 0.02, result 0.87\n")
    with pytest.raises(evaluators.EvaluationError, match="refusing to guess"):
        evaluators.scalar(ambiguous, None, t)
    with pytest.raises(evaluators.EvaluationError, match="no number"):
        evaluators.scalar(_write(tmp_path / "c.txt", "it crashed\n"), None, t)


def test_unknown_evaluator_is_a_clear_error():
    with pytest.raises(evaluators.EvaluationError, match="unknown evaluator"):
        evaluators.get("vibes")


# --------------------------------------------------------------------------
# grading
# --------------------------------------------------------------------------
def _predict_task(tmp_path, threshold=0.7, direction="higher"):
    (tmp_path / "labels").mkdir(exist_ok=True)
    (tmp_path / "labels" / "y.csv").write_text("id,label\na,1\nb,0\nc,1\nd,0\n")
    t = Task.from_dict(_spec(evaluation={"threshold": threshold, "direction": direction}))
    t._dir = tmp_path
    return t


def test_grade_pass_and_fail(tmp_path):
    t = _predict_task(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "prediction.csv").write_text("id,score\na,0.9\nb,0.1\nc,0.8\nd,0.2\n")
    s = scoring.grade(t, out)
    assert s.passed is True and s.measured == pytest.approx(1.0) and s.reason == ""

    (out / "prediction.csv").write_text("id,score\na,0.1\nb,0.9\nc,0.2\nd,0.8\n")
    s = scoring.grade(t, out)
    assert s.passed is False and "needed ≥ 0.7" in s.reason


def test_grade_respects_a_lower_is_better_direction(tmp_path):
    t = _predict_task(tmp_path, threshold=1.5, direction="lower")
    t.evaluation.evaluator = "rmse"
    t.evaluation.metric = "rmse"
    (tmp_path / "labels" / "y.csv").write_text("id,label\na,1.0\nb,3.0\n")
    out = tmp_path / "out"
    out.mkdir()
    (out / "prediction.csv").write_text("id,score\na,2.0\nb,4.0\n")   # rmse 1.0
    assert scoring.grade(t, out).passed is True


def test_ungradable_runs_are_none_not_false(tmp_path):
    """A missing or broken artifact is a harness outcome, never a wrong answer."""
    t = _predict_task(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    s = scoring.grade(t, out)
    assert s.passed is None and "no prediction.csv" in s.reason

    (out / "prediction.csv").write_text("")
    assert scoring.grade(t, out).passed is None

    (out / "prediction.csv").write_text("id,score\nzz,0.5\n")   # ids don't match labels
    s = scoring.grade(t, out)
    assert s.passed is None and "missing" in s.reason


def test_grade_reports_missing_ground_truth_as_ungradable(tmp_path):
    t = _predict_task(tmp_path)
    t.evaluation.labels = "labels/withheld.csv"     # test-split labels not on this box
    out = tmp_path / "out"
    out.mkdir()
    (out / "prediction.csv").write_text("id,score\na,0.9\n")
    s = scoring.grade(t, out)
    assert s.passed is None and "ground truth unavailable" in s.reason


def test_reproduce_grading_uses_a_two_sided_band(tmp_path):
    t = Task.from_dict(_spec(kind="reproduce", output_path="result.txt", evaluation={
        "evaluator": "scalar", "metric": "auroc", "reported": 0.90,
        "direction": "", "threshold": None, "labels": "", "rel_tol": 0.15}))
    out = tmp_path / "out"
    out.mkdir()
    (out / "result.txt").write_text("auroc=0.88\n")
    assert scoring.grade(t, out).passed is True
    (out / "result.txt").write_text("auroc=0.50\n")       # too low
    assert scoring.grade(t, out).passed is False
    (out / "result.txt").write_text("auroc=1.50\n")       # too HIGH is also a fail
    s = scoring.grade(t, out)
    assert s.passed is False and "outside" in s.reason


def test_summarize_excludes_ungradable_from_the_rate():
    S = scoring.Score
    scores = [S("a", True, 0.9, "auroc"), S("b", False, 0.4, "auroc"),
              S("c", None, None, "auroc", "no output")]
    got = scoring.summarize(scores)
    assert got["tasks"] == 3 and got["graded"] == 2 and got["ungradable"] == 1
    assert got["solved"] == 1 and got["revival_rate"] == pytest.approx(0.5)
    assert scoring.summarize([])["revival_rate"] is None


# --------------------------------------------------------------------------
# harness integration
# --------------------------------------------------------------------------
def test_apply_task_score_overrides_an_agents_own_claim(tmp_path):
    """The agent passed its own smoke test; our evaluator disagrees. We win."""
    t = _predict_task(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    (out / "prediction.csv").write_text("id,score\na,0.1\nb,0.9\nc,0.2\nd,0.8\n")
    res = run.BenchmarkResult(repo_url="https://github.com/example/dead",
                              outcome="revived", verified=True)
    run.apply_task_score(res, t, out)
    assert res.outcome == "runs-unverified"
    assert res.task_passed is False and res.task_id == "demo-task"
    assert "needed" in res.notes


def test_apply_task_score_keeps_ungradable_out_of_the_verdict(tmp_path):
    t = _predict_task(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    res = run.BenchmarkResult(repo_url="u", outcome="revived")
    run.apply_task_score(res, t, out)
    assert res.task_passed is None
    assert res.outcome == "revived"          # unchanged — not downgraded
    assert "ungradable" in res.notes


# --------------------------------------------------------------------------
# the real dev-split task, end to end
# --------------------------------------------------------------------------
def test_shipped_dev_tasks_are_valid_and_complete():
    tasks = task_mod.load_tasks(ROOT / "benchmark" / "tasks")
    assert tasks, "no tasks found"
    for t in tasks:
        t.check_files()
        assert len(t.commit) >= 7


def test_scannet_dev_task_grades_real_predictions(tmp_path):
    """Real ScanNet output vs labels recomputed from the deposited structure."""
    import csv

    t = task_mod.load_task(
        ROOT / "benchmark" / "tasks" / "dev" / "scannet-ppi-4zqk" / "task.yaml")
    rows = list(csv.DictReader(
        (ROOT / "pipeline-output" / "scannet" / "predictions_4ZQK_A.csv")
        .read_text().splitlines()))
    out = tmp_path / "out"
    out.mkdir()
    with open(out / "prediction.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["resid", "score"])
        for r in rows:
            w.writerow([r["Residue Index"], r["Binding site probability"]])
    s = scoring.grade(t, out)
    # matches the AUROC the revival recorded on this exact input (0.9233)
    assert s.passed is True
    assert s.measured == pytest.approx(0.9233, abs=5e-4)
