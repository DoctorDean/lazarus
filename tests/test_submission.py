"""Tests for the submission boundary — offline, no Docker daemon.

The boundary's job is to run an agent we know nothing about and still get a trustworthy
score, so these lean on the two ways that goes wrong: the submission being handed the
answer, and a capped run not actually being capped.
"""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmark"))

import submission as sub  # noqa: E402
from lazarus.sandbox import DockerClient  # noqa: E402
from task import Task  # noqa: E402

SHA = "a61623cd98d243c2ff4cd03fc3619d2d22ec50e7"


def _predict_task(tmp_path, **over):
    (tmp_path / "input").mkdir(exist_ok=True)
    (tmp_path / "input" / "in.pdb").write_text("ATOM\n")
    (tmp_path / "labels").mkdir(exist_ok=True)
    (tmp_path / "labels" / "y.csv").write_text("id,label\na,1\nb,0\n")
    spec = {
        "id": "demo-task", "repo_url": "https://github.com/example/dead", "commit": SHA,
        "kind": "predict", "capability": "do a thing", "input_path": "input",
        "output_path": "prediction.csv",
        "evaluation": {"evaluator": "auroc", "metric": "auroc", "direction": "higher",
                       "threshold": 0.7, "labels": "labels/y.csv"},
    }
    spec.update(over)
    t = Task.from_dict(spec)
    t._dir = tmp_path
    return t


class Recorder:
    """Fake docker runner: records argv, returns a scripted result.

    ``raises`` fires only on ``docker run`` — a real daemon that times out a container
    still answers ``rm -f``, and a fake that fails everything would just measure the
    cleanup retry loop.
    """

    def __init__(self, result=(0, "ok", ""), raises=None):
        self.calls, self._result, self._raises = [], result, raises

    def __call__(self, argv, *, input_bytes=None, timeout=None, env=None):
        self.calls.append((list(argv), timeout))
        if self._raises and argv[1:2] == ["run"]:
            raise self._raises
        return self._result


# --------------------------------------------------------------------------
# redaction — the submission must not receive the answer
# --------------------------------------------------------------------------
def test_public_view_strips_the_labels_path(tmp_path):
    t = _predict_task(tmp_path)
    assert "labels" not in t.public_view()["evaluation"]
    # but keeps what a submission legitimately needs
    ev = t.public_view()["evaluation"]
    assert ev["metric"] == "auroc" and ev["direction"] == "higher" and ev["threshold"] == 0.7


def test_public_view_strips_the_reported_value_of_a_reproduce_task():
    """For `reproduce`, `reported` IS the answer — echo it back and you score perfectly."""
    t = Task.from_dict({
        "id": "r", "repo_url": "https://github.com/e/d", "commit": SHA,
        "kind": "reproduce", "capability": "c", "output_path": "result.txt",
        "evaluation": {"evaluator": "scalar", "metric": "ci", "reported": 0.878}})
    ev = t.public_view()["evaluation"]
    assert "reported" not in ev
    assert ev["metric"] == "ci"
    assert "0.878" not in yaml.safe_dump(t.public_view())


def test_staging_copies_input_but_never_labels(tmp_path):
    t = _predict_task(tmp_path)
    staged = sub.stage_task(t, tmp_path / "staged")
    names = {p.name for p in staged.rglob("*")}
    assert "in.pdb" in names and "task.yaml" in names
    assert "y.csv" not in names and not (staged / "labels").exists()
    spec = yaml.safe_load((staged / "task.yaml").read_text())
    assert "labels" not in spec["evaluation"]


def test_staging_refuses_when_ground_truth_would_leak(tmp_path):
    """A task whose input *is* the label file must not be staged silently."""
    t = _predict_task(tmp_path)
    (tmp_path / "input" / "in.pdb").write_text(
        (tmp_path / "labels" / "y.csv").read_text())     # same bytes as the answer key
    with pytest.raises(sub.SubmissionError, match="leaked the ground truth"):
        sub.stage_task(t, tmp_path / "staged")


def test_staging_handles_a_single_file_input(tmp_path):
    t = _predict_task(tmp_path, input_path="input/in.pdb")
    staged = sub.stage_task(t, tmp_path / "staged")
    assert (staged / "input" / "in.pdb").exists()


def test_staging_rejects_a_missing_input(tmp_path):
    t = _predict_task(tmp_path, input_path="input/nope.pdb")
    with pytest.raises(sub.SubmissionError, match="does not exist"):
        sub.stage_task(t, tmp_path / "staged")


# --------------------------------------------------------------------------
# the container invocation
# --------------------------------------------------------------------------
def test_argv_mounts_task_read_only_and_out_writable(tmp_path):
    t = _predict_task(tmp_path)
    s = sub.Submission(name="agentx", image="ghcr.io/x/agent:1")
    argv = sub.build_argv(s, t, tmp_path / "staged", tmp_path / "out")
    joined = " ".join(argv)
    assert f"{tmp_path / 'staged'}:/task:ro" in joined
    assert f"{tmp_path / 'out'}:/out" in joined and ":/out:ro" not in joined
    assert "--repo-url https://github.com/example/dead" in joined
    assert f"--commit {SHA}" in joined
    assert "--task /task/task.yaml --out /out" in joined
    assert argv[argv.index("--network") + 1] == "none"    # closed by default


def test_argv_uses_the_artifact_pin_for_non_git_sources(tmp_path):
    t = _predict_task(tmp_path, commit="", artifact_url="https://sf.net/f.tar.gz",
                      artifact_sha256="d" * 64)
    argv = sub.build_argv(sub.Submission("a", "img"), t, tmp_path, tmp_path / "o")
    joined = " ".join(argv)
    assert "--artifact-url https://sf.net/f.tar.gz" in joined
    assert f"--artifact-sha256 {'d' * 64}" in joined and "--commit" not in joined


def test_argv_passes_resource_caps_and_extra_args(tmp_path):
    t = _predict_task(tmp_path)
    s = sub.Submission("a", "img", extra_args=["--beam", "4"])
    argv = sub.build_argv(s, t, tmp_path, tmp_path / "o",
                          network="lazarus-bench", gpus="all", memory="16g", cpus="4")
    assert argv[argv.index("--network") + 1] == "lazarus-bench"
    assert argv[argv.index("--gpus") + 1] == "all"
    assert argv[argv.index("--memory") + 1] == "16g"
    assert argv[argv.index("--cpus") + 1] == "4"
    assert argv[-2:] == ["--beam", "4"]


def test_run_applies_the_wall_clock_cap_from_the_task(tmp_path):
    t = _predict_task(tmp_path)
    t.caps.wall_clock_s = 1234
    rec = Recorder()
    run = sub.run_submission(sub.Submission("a", "img"), t, tmp_path / "w",
                             client=DockerClient(runner=rec))
    assert run.ok and run.exit_code == 0
    _argv, timeout = rec.calls[-1]
    assert timeout == 1234


def test_a_timed_out_run_is_marked_and_the_container_killed(tmp_path):
    t = _predict_task(tmp_path)
    rec = Recorder(raises=TimeoutError("deadline"))
    run = sub.run_submission(sub.Submission("a", "img"), t, tmp_path / "w",
                             client=DockerClient(runner=rec))
    assert run.timed_out and not run.ok
    # every call after the failed `run` must be a force-remove of our container
    kills = [c for c, _ in rec.calls if c[1:3] == ["rm", "-f"]]
    assert kills, "a capped run whose container survives keeps burning the host"


def test_run_and_grade_scores_the_artifact_a_submission_wrote(tmp_path):
    t = _predict_task(tmp_path)

    def writer(argv, *, input_bytes=None, timeout=None, env=None):
        out = Path(argv[argv.index("-v", argv.index("-v") + 1) + 1].split(":")[0])
        (out / "prediction.csv").write_text("id,score\na,0.9\nb,0.1\n")
        return (0, "", "")

    run, score = sub.run_and_grade(sub.Submission("a", "img"), t, tmp_path / "w",
                                   client=DockerClient(runner=writer))
    assert run.ok and score.passed is True and score.measured == pytest.approx(1.0)


def test_a_crashed_submission_is_still_graded_on_what_it_wrote(tmp_path):
    """A crash after a correct write is not a wrong answer."""
    t = _predict_task(tmp_path)

    def crasher(argv, *, input_bytes=None, timeout=None, env=None):
        out = Path(argv[argv.index("-v", argv.index("-v") + 1) + 1].split(":")[0])
        (out / "prediction.csv").write_text("id,score\na,0.9\nb,0.1\n")
        return (1, "", "segfault")

    run, score = sub.run_and_grade(sub.Submission("a", "img"), t, tmp_path / "w",
                                   client=DockerClient(runner=crasher))
    assert not run.ok and score.passed is True


def test_a_submission_that_writes_nothing_is_ungradable_not_wrong(tmp_path):
    t = _predict_task(tmp_path)
    run, score = sub.run_and_grade(sub.Submission("a", "img"), t, tmp_path / "w",
                                   client=DockerClient(runner=Recorder()))
    assert run.ok and score.passed is None and "no prediction.csv" in score.reason
