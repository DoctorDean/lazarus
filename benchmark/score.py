#!/usr/bin/env python3
"""Grading — turn a submission's output directory into a pass/fail for one task.

Measurement (``evaluators``) and judgement (here) are deliberately separate: the
evaluator returns a number, this module decides whether the number clears the task's
bar, in the task's declared direction. Nothing here consults the submission's opinion
of its own success.

Three outcomes, and the third matters as much as the first two:

``passed=True``   the measured metric cleared the threshold (or landed in the band)
``passed=False``  it didn't — a real, reportable failure
``passed=None``   the harness could not grade it at all (no output, unparseable,
                  evaluator error). Never scored as a failure of the *method*: it goes
                  in a separate bucket so a broken grader can't quietly deflate a rate.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

import evaluators
from task import Task


@dataclass
class Score:
    task_id: str
    passed: Optional[bool]          # None = could not evaluate (see module docstring)
    measured: Optional[float]
    metric: str
    reason: str = ""                # why it failed, or why it couldn't be graded

    def to_dict(self) -> dict:
        return asdict(self)


def compare(measured: float, task: Task) -> bool:
    """Judge a measured value against the task's criterion. No inference anywhere."""
    e = task.evaluation
    if task.kind == "reproduce":
        # two-sided relative band around the paper's published value
        return abs(measured - e.reported) <= e.rel_tol * abs(e.reported)
    if e.direction == "higher":
        return measured >= e.threshold
    if e.direction == "lower":
        return measured <= e.threshold
    # validate() rejects this at load time; belt-and-braces so a hand-built Task
    # can never silently grade in an undefined direction.
    raise ValueError(f"{task.id}: no direction to compare in (got {e.direction!r})")


def grade(task: Task, out_dir) -> Score:
    """Grade one submission output directory against one task."""
    out_dir = Path(out_dir)
    prediction = out_dir / task.output_path
    if not prediction.exists():
        return Score(task.id, None, None, task.evaluation.metric,
                     f"submission produced no {task.output_path}")
    if prediction.stat().st_size == 0:
        return Score(task.id, None, None, task.evaluation.metric,
                     f"{task.output_path} is empty")

    labels = task.labels_file
    if task.kind == "predict" and (labels is None or not labels.exists()):
        # Withheld on purpose for the test split — a missing label file is an operator
        # error, not a submission failure, so it must not read as a wrong answer.
        return Score(task.id, None, None, task.evaluation.metric,
                     f"ground truth unavailable for {task.id} (labels: {labels})")

    try:
        fn = evaluators.get(task.evaluation.evaluator)
        measured = float(fn(prediction, labels, task))
    except evaluators.EvaluationError as exc:
        return Score(task.id, None, None, task.evaluation.metric, str(exc))
    except Exception as exc:  # noqa: BLE001 — a grader bug must not kill the sweep
        return Score(task.id, None, None, task.evaluation.metric,
                     f"evaluator {task.evaluation.evaluator!r} raised "
                     f"{type(exc).__name__}: {exc}")

    passed = compare(measured, task)
    e = task.evaluation
    if passed:
        reason = ""
    elif task.kind == "reproduce":
        reason = (f"{e.metric}={measured:.4g} outside ±{e.rel_tol:.0%} of the "
                  f"reported {e.reported:.4g}")
    else:
        arrow = "≥" if e.direction == "higher" else "≤"
        reason = f"{e.metric}={measured:.4g}, needed {arrow} {e.threshold:.4g}"
    return Score(task.id, passed, measured, e.metric, reason)


def summarize(scores: list) -> dict:
    """Aggregate a sweep. ``ungradable`` is reported, never folded into the rate.

    The denominator is *graded* tasks. Silently counting ungradable runs as failures
    would let a harness bug look like a weak agent.
    """
    graded = [s for s in scores if s.passed is not None]
    solved = [s for s in graded if s.passed]
    return {
        "tasks": len(scores),
        "graded": len(graded),
        "ungradable": len(scores) - len(graded),
        "solved": len(solved),
        "revival_rate": (len(solved) / len(graded)) if graded else None,
    }
