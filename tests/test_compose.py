"""Tests for Lazarus Compose — offline, no Docker daemon."""

import os

import pytest

from lazarus.compose import (
    Pipeline,
    Registry,
    Runner,
    Step,
    StepResult,
    _deps_of,
    toposort,
)
from lazarus.contract import Contract
from lazarus.sandbox import DockerClient

PIPE_YAML = """
name: demo
inputs:
  structure: {type: path:pdb}
steps:
  - id: a
    uses: comp_a
    with: {INPUT: "${inputs.structure}", CHAIN: A}
  - id: b
    uses: comp_b
    with: {x: "${a.scores}"}
outputs:
  result: "${b.out}"
"""


def test_pipeline_parse():
    p = Pipeline.from_yaml(PIPE_YAML)
    assert p.name == "demo"
    assert [s.id for s in p.steps] == ["a", "b"]
    assert p.steps[0].with_["CHAIN"] == "A"
    assert p.outputs["result"] == "${b.out}"


def test_deps_and_toposort():
    p = Pipeline.from_yaml(PIPE_YAML)
    assert _deps_of(p.steps[1]) == {"a"}
    assert _deps_of(p.steps[0]) == set()
    order = [s.id for s in toposort(p.steps)]
    assert order.index("a") < order.index("b")


def test_toposort_detects_cycle():
    steps = [Step("a", "x", {"v": "${b.o}"}), Step("b", "y", {"v": "${a.o}"})]
    with pytest.raises(ValueError):
        toposort(steps)


def test_registry_from_dirs(tmp_path):
    c = Contract(name="comp_a", repo_url="", base_image="img:a", entrypoint="echo hi")
    d = tmp_path / "comp_a"
    d.mkdir()
    (d / "lazarus.yaml").write_text(c.to_yaml())
    reg = Registry.from_dirs([tmp_path])
    assert reg.get("comp_a").base_image == "img:a"
    with pytest.raises(KeyError):
        reg.get("missing")


def test_resolve_refs(tmp_path):
    r = Runner(Registry({}))
    sdir = tmp_path / "a"
    sdir.mkdir()
    (sdir / "pred_scores.npy").write_text("x")
    ctx = {
        "inputs": {"structure": str(tmp_path / "in.pdb")},
        "steps": {"a": StepResult("a", str(sdir), [])},
    }
    assert r._resolve("A", ctx) == ("literal", "A")
    assert r._resolve("${inputs.structure}", ctx)[0] == "file"
    kind, val = r._resolve("${a.scores}", ctx)
    assert kind == "file" and val.endswith("pred_scores.npy")
    with pytest.raises(FileNotFoundError):
        r._resolve("${a.nomatch}", ctx)


def test_resolve_ref_finds_nested_step_output(tmp_path):
    """DiffDock writes $OUTDIR/<complex_name>/rank1.sdf, so the artifact glob recurses."""
    r = Runner(Registry({}))
    sdir = tmp_path / "diffdock"
    (sdir / "target").mkdir(parents=True)
    (sdir / "target" / "rank1.sdf").write_text("pose")
    ctx = {"inputs": {}, "steps": {"diffdock": StepResult("diffdock", str(sdir), [])}}
    kind, val = r._resolve("${diffdock.rank1}", ctx)
    assert kind == "file" and val.endswith(os.path.join("target", "rank1.sdf"))


def test_resolve_ref_skips_directories_matching_the_selector(tmp_path):
    """A dir whose name matches must not shadow the real file (it sorts first here)."""
    r = Runner(Registry({}))
    sdir = tmp_path / "a"
    (sdir / "rank1_out").mkdir(parents=True)      # sorts before zz_rank1.sdf
    (sdir / "zz_rank1.sdf").write_text("pose")
    ctx = {"inputs": {}, "steps": {"a": StepResult("a", str(sdir), [])}}
    kind, val = r._resolve("${a.rank1}", ctx)
    assert kind == "file" and val.endswith("zz_rank1.sdf")


def test_run_component_prepares_shared_dirs_as_root(tmp_path):
    """Bricks that run as a non-root user (DiffDock's appuser) still need to read
    /lazarus/in and write /lazarus/out — so the dirs are made root + world-writable,
    while the entrypoint itself keeps the image's own user."""
    calls = []

    def fake(argv, *, input_bytes=None, timeout=None, env=None):
        calls.append(list(argv))
        return (0, "", "")

    r = Runner(Registry({}))
    r.client = DockerClient(runner=fake)
    c = Contract(name="c", repo_url="", base_image="img:x", entrypoint="run-me")
    r._run_component(c, {}, tmp_path / "out")

    joined = [" ".join(a) for a in calls]
    prep = [j for j in joined if "mkdir -p /lazarus/in" in j]
    assert prep, "shared work dirs were never created"
    assert "--user 0" in prep[0] and "chmod -R 777 /lazarus" in prep[0]
    entry = [j for j in joined if j.endswith("bash -lc run-me")]
    assert entry and "--user" not in entry[0]


def test_run_component_issues_expected_docker_sequence(tmp_path):
    calls = []

    def fake(argv, *, input_bytes=None, timeout=None, env=None):
        calls.append(list(argv))
        return (0, "", "")

    r = Runner(Registry({}))
    r.client = DockerClient(runner=fake)   # inject fake for offline test
    c = Contract(name="c", repo_url="", base_image="img:x",
                 entrypoint="run $INPUT $OUTDIR", gpus="all")
    inp = tmp_path / "in.pdb"
    inp.write_text("data")
    resolved = {"INPUT": ("file", str(inp)), "CHAIN": ("literal", "A")}
    r._run_component(c, resolved, tmp_path / "out")

    joined = [" ".join(a) for a in calls]
    assert any("run -d" in j and "--gpus all" in j for j in joined)          # GPU start
    assert any(" cp " in f" {j} " and "in.pdb" in j for j in joined)          # input copied in
    assert any("exec" in j and "run $INPUT $OUTDIR" in j for j in joined)     # entrypoint run
    assert any("rm -f" in j for j in joined)                                  # container removed
