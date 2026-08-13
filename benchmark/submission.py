#!/usr/bin/env python3
"""The submission boundary — run *someone else's* agent against a task.

``run.py`` imports ``lazarus.scout`` and ``lazarus.resurrect`` directly, so it can only
ever run Lazarus. A leaderboard needs the agent to be an opaque artifact, which is what
this module defines: a submission is a **Docker image with a fixed CLI**, and the harness
knows nothing else about it.

    docker run --rm --network <net> -v <staged>:/task:ro -v <out>:/out <image> \
        --repo-url <url> --commit <sha> --task /task/task.yaml --out /out

The submission writes the task's declared ``output_path`` into ``/out``; the harness then
grades that artifact with ``score.grade``. Everything about *how* it revives the repo is
its own business.

Two things this module is responsible for that are easy to get wrong:

**Staging.** The task directory holds ``labels/`` next to ``input/``. Mounting it whole
would hand over the answer key. :func:`stage_task` copies only the input and a *redacted*
spec (:meth:`Task.public_view`), and it refuses to stage anything that would leak ground
truth.

**Caps.** Only some caps are actually enforceable against an opaque container — see
:class:`Caps` handling in :func:`run_submission`. Pretending otherwise would put
unenforceable numbers in the rules.
"""
from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import yaml

TASK_MOUNT = "/task"
OUT_MOUNT = "/out"


class SubmissionError(Exception):
    """The submission could not be run (staging failed, image missing, bad spec)."""


@dataclass
class Submission:
    """An opaque agent: an image plus the identity we report it under."""

    name: str
    image: str
    extra_args: list = field(default_factory=list)   # passed through after the fixed CLI


@dataclass
class SubmissionRun:
    submission: str
    task_id: str
    exit_code: Optional[int] = None
    timed_out: bool = False
    wall_clock_s: float = 0.0
    out_dir: str = ""
    log_tail: str = ""

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------
# staging — what the submission is allowed to see
# --------------------------------------------------------------------------
def stage_task(task, dest) -> Path:
    """Build the read-only ``/task`` tree: redacted ``task.yaml`` + ``input/`` only.

    Never copies ``labels/``. The check at the end is not decoration — a staging bug that
    leaked the answer key would silently invalidate every score that followed, and it
    would look like a very good submission rather than a broken harness.
    """
    dest = Path(dest)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    (dest / "task.yaml").write_text(
        yaml.safe_dump(task.public_view(), sort_keys=False, allow_unicode=True),
        encoding="utf-8")

    src = task.input_file
    if src is not None:
        if not src.exists():
            raise SubmissionError(f"{task.id}: input {src} does not exist")
        if src.is_dir():
            shutil.copytree(src, dest / "input")
        else:
            (dest / "input").mkdir()
            shutil.copy(src, dest / "input" / src.name)

    labels = task.labels_file
    if labels is not None and labels.exists():
        leaked = [p for p in dest.rglob("*")
                  if p.is_file() and p.read_bytes() == labels.read_bytes()]
        if leaked:
            raise SubmissionError(
                f"{task.id}: staging leaked the ground truth into "
                f"{[str(p.relative_to(dest)) for p in leaked]} — refusing to run")
    staged_spec = (dest / "task.yaml").read_text()
    for banned in ("labels:", "reported:"):
        if banned in staged_spec:
            raise SubmissionError(
                f"{task.id}: redacted spec still contains {banned!r} — refusing to run")
    return dest


# --------------------------------------------------------------------------
# running
# --------------------------------------------------------------------------
def build_argv(submission: Submission, task, staged: Path, out_dir: Path, *,
               network: str = "none", gpus: Optional[str] = None,
               memory: Optional[str] = None, cpus: Optional[str] = None,
               name: Optional[str] = None) -> list:
    """The exact ``docker`` argv for one submission run. Pure — unit-tested."""
    argv = ["run", "--rm"]
    if name:
        argv += ["--name", name]
    argv += ["--network", network]
    if gpus:
        argv += ["--gpus", gpus]
    if memory:
        argv += ["--memory", memory]
    if cpus:
        argv += ["--cpus", cpus]
    argv += ["-v", f"{staged}:{TASK_MOUNT}:ro", "-v", f"{out_dir}:{OUT_MOUNT}"]
    argv += [submission.image,
             "--repo-url", task.repo_url,
             "--task", f"{TASK_MOUNT}/task.yaml",
             "--out", OUT_MOUNT]
    if task.pin_kind == "git":
        argv += ["--commit", task.commit]
    else:
        argv += ["--artifact-url", task.artifact_url,
                 "--artifact-sha256", task.artifact_sha256]
    return argv + list(submission.extra_args)


def run_submission(submission: Submission, task, work_dir, *, client,
                   network: str = "none", gpus: Optional[str] = None,
                   memory: Optional[str] = None, cpus: Optional[str] = None,
                   timeout_s: Optional[int] = None,
                   kill_budget_s: float = 30.0) -> SubmissionRun:
    """Stage the task, run the submission container under caps, return what happened.

    **Which caps are real.** ``wall_clock_s`` is enforced here, and ``memory``/``cpus``
    are enforced by the container runtime. ``turns`` and ``cost_usd`` are *internal to an
    agent* — an opaque image has no obligation to report them and the harness cannot
    observe them. They stay in the task spec as guidance for the reference submission and
    as self-reported metadata, but they are not rules, and nothing may be ranked on them.
    Writing them down as enforced caps would be a rule we cannot apply.
    """
    work_dir = Path(work_dir)
    staged = stage_task(task, work_dir / "task")
    out_dir = work_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = timeout_s if timeout_s is not None else task.caps.wall_clock_s
    cname = f"lzb-{submission.name}-{task.id}"[:60]
    argv = build_argv(submission, task, staged, out_dir, network=network, gpus=gpus,
                      memory=memory, cpus=cpus, name=cname)

    run = SubmissionRun(submission=submission.name, task_id=task.id, out_dir=str(out_dir))
    t0 = time.monotonic()
    try:
        cr = client.run(argv, timeout=cap)
        run.exit_code = cr.exit_code
        run.log_tail = ((cr.stdout or "") + "\n" + (cr.stderr or ""))[-4000:]
    except Exception as exc:  # noqa: BLE001 — a timeout or a dead host both land here
        run.timed_out = True
        run.log_tail = f"{type(exc).__name__}: {exc}"
        # A capped run whose container survives would keep burning the host. run.py learned
        # this the hard way (a 90-minute cap that ran 11.7 hours), so kill by name and
        # retry rather than trusting one rm. Budget is short and bounded: this is per-task
        # cleanup of a `--rm` container, not the long teardown of a live sandbox, and a
        # wedged daemon must not add minutes to every task in a sweep.
        try:
            from run import _force_remove
            _force_remove(client, cname, budget_s=kill_budget_s)
        except Exception:  # noqa: BLE001
            pass
    run.wall_clock_s = time.monotonic() - t0
    return run


def run_and_grade(submission: Submission, task, work_dir, *, client, **kw) -> tuple:
    """Run a submission, then grade its output. Returns ``(SubmissionRun, Score)``.

    A submission that crashes or times out is still graded, because the artifact it
    managed to write is what counts — and a crash after a correct write should not be
    scored as a wrong answer. ``score.grade`` reports "no output" as *ungradable*, which
    keeps it out of the rate denominator either way.
    """
    import score as _score

    run = run_submission(submission, task, work_dir, client=client, **kw)
    return run, _score.grade(task, run.out_dir)
