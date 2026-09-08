"""Integration checks for the submission boundary — these need a real Docker daemon.

The rest of the suite is hermetic (fake runners, no daemon) and finishes in under a
second, which is what makes it worth running constantly. These do not belong in that
budget, so they are opt-in::

    LAZARUS_DOCKER_TESTS=1 pytest -q tests/test_reference_integration.py

They exist because the P2 boundary was fully unit-tested and still broken in four
places: a Dockerfile written into a read-only ``/task``, a missing ``docker`` client
(Debian trixie puts it in ``docker-cli``, not ``docker.io``), no way to pass the
submission a credential or a socket, and ``docker build`` falling back to the legacy
builder — which cannot export a cross-platform image. Every one of those is invisible to
a mocked runner and fatal to a real run.
"""
import csv
import json
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "benchmark"))
sys.path.insert(0, str(ROOT / "benchmark" / "reference"))
sys.path.insert(0, str(ROOT / "src"))

pytestmark = pytest.mark.skipif(
    not os.environ.get("LAZARUS_DOCKER_TESTS"),
    reason="needs a Docker daemon; set LAZARUS_DOCKER_TESTS=1 to run")

import score as _score                                          # noqa: E402
import submission as sub                                         # noqa: E402
from task import load_task                                       # noqa: E402

TASK = ROOT / "benchmark/tasks/dev/scannet-ppi-4zqk/task.yaml"
NATIVE = ROOT / "pipeline-output/scannet/predictions_4ZQK_A.csv"
KNOWN_AUROC = 0.9233        # what the original revival measured on this input


def _client():
    from lazarus.sandbox import DockerClient, find_docker
    c = DockerClient(binary=find_docker())
    if not c.available():
        pytest.skip("no Docker daemon answering")
    return c


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores mode bits; needs a :ro mount")
def test_bake_does_not_write_into_the_task_dir(tmp_path):
    """``/task`` is mounted read-only, so the derived image cannot be built from it.

    The original code dropped ``Dockerfile.lazarus-bench`` next to the input, which fails
    with EROFS on every real run. Nothing may be written into the task tree at all.
    """
    import lazarus_submission as ref

    task = load_task(TASK)
    staged = sub.stage_task(task, tmp_path / "task")
    before = {p.relative_to(staged) for p in staged.rglob("*")}
    os.chmod(staged, 0o500)
    try:
        ref.bake_input_image("alpine:3.20", staged,
                             "lazarus-bench-input:pytest", client=_client())
    finally:
        os.chmod(staged, 0o700)
    assert {p.relative_to(staged) for p in staged.rglob("*")} == before


def test_boundary_grades_a_conforming_submission_at_the_known_answer(tmp_path):
    """Drive the real contract with a stub that stands in for a submission that worked.

    The stub does the one thing the contract demands and the harness must not do for it:
    convert the method's *native* output (``Model,Chain,Residue Index,...``) into the
    task's declared ``resid,score``. Everything else here is the production path —
    staging, the argv, the mounts, the exit code, and ``score.grade``.
    """
    if not NATIVE.exists():
        pytest.skip(f"no recorded ScanNet prediction at {NATIVE}")
    client = _client()

    ctx = tmp_path / "stub"
    ctx.mkdir()
    shutil.copy(NATIVE, ctx / "native.csv")
    (ctx / "agent.py").write_text(textwrap.dedent('''
        import argparse, csv, json, pathlib
        ap = argparse.ArgumentParser()
        for f in ("--repo-url", "--commit", "--task", "--out",
                  "--artifact-url", "--artifact-sha256"):
            ap.add_argument(f, default="")
        a = ap.parse_args()

        # What did the harness actually expose to us? Recorded so the test can assert
        # from *inside* the container that the answer key never crossed the boundary.
        task_dir = pathlib.Path(a.task).parent
        (pathlib.Path(a.out) / "saw.json").write_text(json.dumps(
            sorted(str(p.relative_to(task_dir)) for p in task_dir.rglob("*"))))

        spec = pathlib.Path(a.task).read_text()
        rows = list(csv.DictReader(open("/native.csv")))
        out = pathlib.Path(a.out) / "prediction.csv"
        with out.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["resid", "score"])            # the task's declared schema
            for r in rows:
                w.writerow([r["Residue Index"], r["Binding site probability"]])
        (pathlib.Path(a.out) / "spec_seen.txt").write_text(spec)
    ''').strip())
    (ctx / "Dockerfile").write_text(
        "FROM python:3.12-slim\n"
        "COPY native.csv /native.csv\n"
        "COPY agent.py /agent.py\n"
        'ENTRYPOINT ["python", "/agent.py"]\n')
    client.run(["build", "-t", "lazarus-stub:pytest", str(ctx)],
               timeout=900).raise_for_status()

    task = load_task(TASK)
    run, score = sub.run_and_grade(
        sub.Submission(name="stub", image="lazarus-stub:pytest"), task,
        tmp_path / "work", client=client, network="none")

    assert run.ok, run.log_tail
    assert score.passed is True
    assert score.measured == pytest.approx(KNOWN_AUROC, abs=5e-4)

    # The submission's own view of /task: input and spec, never the answer key.
    saw = json.loads((Path(run.out_dir) / "saw.json").read_text())
    assert "labels" not in saw and not any("interface_5A" in p for p in saw)
    assert "input/4ZQK_A.pdb" in saw and "task.yaml" in saw

    # ...and the spec it read leaks neither the labels path nor a calibrating number.
    spec_seen = (Path(run.out_dir) / "spec_seen.txt").read_text()
    for leak in ("labels", "reported", "0.9233"):
        assert leak not in spec_seen, f"{leak!r} reached the submission"
