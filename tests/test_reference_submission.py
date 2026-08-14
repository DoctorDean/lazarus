"""Tests for the reference submission's goal construction.

`build_goal` is the single point where a benchmark task becomes an agent's objective, so
what it must and must not say is worth pinning precisely. The orchestration around it
needs Docker, an API key and real compute, so it isn't exercised here.
"""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmark"))
sys.path.insert(0, str(ROOT / "benchmark" / "reference"))

import lazarus_submission as ref  # noqa: E402
from task import Task, load_tasks  # noqa: E402

SHA = "a61623cd98d243c2ff4cd03fc3619d2d22ec50e7"
URL = "https://github.com/example/dead"


def _predict_spec(**over):
    d = {
        "id": "t", "repo_url": URL, "commit": SHA, "kind": "predict",
        "capability": "score every residue for interface membership",
        "input_path": "input", "output_path": "prediction.csv",
        "output_schema": ["resid", "score"],
        "evaluation": {"evaluator": "auroc", "metric": "auroc", "direction": "higher",
                       "threshold": 0.7, "labels": "labels/y.csv"},
    }
    d.update(over)
    return d


def test_goal_pins_the_commit_and_warns_against_a_shallow_clone():
    g = ref.build_goal(_predict_spec(), URL, commit=SHA)
    assert SHA in g and f"git checkout {SHA}" in g
    assert "depth 1" in g and "HEAD is not what is being measured" in g


def test_goal_uses_checksum_verification_for_an_artifact_pin():
    g = ref.build_goal(_predict_spec(), URL, artifact_url="https://sf.net/f.tgz",
                       artifact_sha256="a" * 64)
    assert "sha256sum -c" in g and "a" * 64 in g
    assert "git checkout" not in g


def test_goal_states_the_exact_output_contract():
    g = ref.build_goal(_predict_spec(), URL, commit=SHA)
    assert f"{ref.IN_CONTAINER_OUT}/prediction.csv" in g
    assert "`resid,score`" in g
    assert f"{ref.IN_CONTAINER_OUT}/input" in g
    assert "exactly once" in g


def test_goal_never_points_the_agent_at_the_submission_containers_mounts():
    """The agent runs in a *revival* container: /out and /task don't exist there.

    Its tools only reach its own filesystem, so telling it to write /out would silently
    produce nothing — the failure this wrapper originally had.
    """
    for spec in (_predict_spec(),
                 _predict_spec(kind="reproduce", output_path="result.txt",
                              output_schema=[],
                              evaluation={"evaluator": "scalar", "metric": "ci"})):
        g = ref.build_goal(spec, URL, commit=SHA)
        assert "/out/" not in g and "/task/" not in g
        assert ref.IN_CONTAINER_OUT in g


def test_goal_carries_the_tasks_criterion_not_an_invented_one():
    g = ref.build_goal(_predict_spec(), URL, commit=SHA)
    assert "auroc" in g and "0.7" in g and "higher" in g
    assert "Do not invent your own success metric" in g


def test_goal_respects_a_lower_is_better_direction():
    g = ref.build_goal(_predict_spec(evaluation={
        "evaluator": "ligand_centroid_distance", "metric": "centroid_distance_A",
        "direction": "lower", "threshold": 2.0}), URL, commit=SHA)
    assert "lower is better" in g and "≤ 2.0" in g


def test_reproduce_goal_demands_a_measured_value_and_forbids_guessing():
    g = ref.build_goal(_predict_spec(kind="reproduce", output_path="result.txt",
                                     output_schema=[],
                                     evaluation={"evaluator": "scalar",
                                                 "metric": "concordance_index"}),
                       URL, commit=SHA)
    assert "concordance_index=<value>" in g
    assert "Do NOT write a value you did not measure" in g
    assert "If you cannot run the benchmark, write no file." in g


def test_goal_leaks_no_ground_truth_even_from_an_unredacted_spec():
    """Defence in depth, and the *second* independent layer.

    Staging is what redacts the spec a submission receives (covered in
    test_submission.py). This asserts the other half: `build_goal` must not propagate
    ground truth into the agent's instructions even when handed the FULL task — so it is
    fed `to_dict()`, not `public_view()`, on purpose. If it were fed the redacted view the
    assertion would hold trivially and test nothing.
    """
    tasks = load_tasks(ROOT / "benchmark" / "tasks")
    assert tasks
    checked_labels = checked_reported = 0
    for t in tasks:
        g = ref.build_goal(t.to_dict(), t.repo_url, commit=t.commit,
                           artifact_url=t.artifact_url,
                           artifact_sha256=t.artifact_sha256)
        if t.evaluation.labels:
            assert t.evaluation.labels not in g, f"{t.id}: goal leaks the labels path"
            checked_labels += 1
        if t.evaluation.reported is not None:
            assert str(t.evaluation.reported) not in g, f"{t.id}: goal leaks the answer"
            checked_reported += 1
        assert t.commit in g or t.artifact_sha256 in g, f"{t.id}: goal does not pin the source"
    # the corpus must actually contain both kinds of secret, or this proves nothing
    assert checked_labels and checked_reported


def test_cli_requires_a_pin():
    with pytest.raises(SystemExit):
        ref.main(["--task", "/nope", "--out", "/tmp"])          # no --repo-url
    assert ref.main(["--repo-url", URL, "--task", "/nope", "--out", "/tmp"]) == 2


def test_goal_builds_for_every_shipped_task_without_error():
    tasks = load_tasks(ROOT / "benchmark" / "tasks")
    assert tasks
    for t in tasks:
        g = ref.build_goal(t.public_view(), t.repo_url, commit=t.commit,
                           artifact_url=t.artifact_url,
                           artifact_sha256=t.artifact_sha256)
        assert t.capability.split()[0] in g and len(g) > 400
