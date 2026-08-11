#!/usr/bin/env python3
"""Evaluators — the harness's graders.

An evaluator reads a submission's output artifact plus (for ``predict`` tasks) the
withheld ground truth, and returns **one number**: the measured metric. It does not
decide pass/fail — ``score.grade`` does that, by comparing to the task's threshold in
the task's declared direction. Keeping measurement and judgement apart means a task can
change its bar without touching an evaluator.

Evaluators are *our* code, so they run in-process — no container needed. The
**submission** is the untrusted party, not the grader. What is untrusted here is the
submission's *output file*, so every parser below is defensive: malformed, truncated,
mis-keyed and non-numeric content must raise :class:`EvaluationError`, never crash the
sweep or silently score 0.

Signature::

    evaluate(prediction: Path, labels: Path | None, task) -> float
"""
from __future__ import annotations

import csv
import math
import re
from pathlib import Path
from typing import Optional

import numpy as np


class EvaluationError(Exception):
    """The submission's output could not be graded (missing, malformed, unparseable)."""


_NUM = r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"


def _read_rows(path: Path) -> list:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise EvaluationError(f"cannot read {path.name}: {exc}") from exc
    rows = list(csv.DictReader(text.splitlines()))
    if not rows:
        raise EvaluationError(f"{path.name} has no data rows")
    return rows


def _column(rows: list, *names: str) -> list:
    """Fetch the first column matching any of ``names`` (case/space-insensitive)."""
    if not rows:
        raise EvaluationError("no rows")
    norm = {(k or "").strip().lower().replace(" ", "_"): k for k in rows[0]}
    for want in names:
        key = norm.get(want.lower())
        if key is not None:
            return [r.get(key) for r in rows]
    raise EvaluationError(
        f"none of the expected columns {list(names)} found; got {sorted(norm)}")


def _floats(values: list, what: str) -> "np.ndarray":
    out = []
    for i, v in enumerate(values):
        try:
            f = float(str(v).strip())
        except (TypeError, ValueError):
            raise EvaluationError(f"{what}: row {i} is not a number: {v!r}") from None
        if math.isnan(f) or math.isinf(f):
            raise EvaluationError(f"{what}: row {i} is {v!r} — not a finite number")
        out.append(f)
    return np.asarray(out, dtype=float)


def _rankdata(a: "np.ndarray") -> "np.ndarray":
    """Average ranks, ties shared — the scipy ``rankdata(method='average')`` algorithm.

    Ties matter: a submission that emits a constant score would otherwise get an
    arbitrary AUROC instead of the correct 0.5.
    """
    sorter = np.argsort(a, kind="mergesort")
    inv = np.empty(len(a), dtype=int)
    inv[sorter] = np.arange(len(a))
    a_sorted = a[sorter]
    obs = np.r_[True, a_sorted[1:] != a_sorted[:-1]]
    dense = obs.cumsum()[inv]
    count = np.r_[np.nonzero(obs)[0], len(a)]
    return 0.5 * (count[dense] + count[dense - 1] + 1)


def _align(pred_rows: list, label_rows: list, id_names, score_names, label_names):
    """Join predictions to labels on their id column. Order is never assumed.

    A submission controls its own row order, so aligning positionally would let a
    shuffled-but-correct output score as noise — and a sorted-by-score output score
    far too well.
    """
    pid = [str(x).strip() for x in _column(pred_rows, *id_names)]
    pscore = _floats(_column(pred_rows, *score_names), "prediction score")
    lid = [str(x).strip() for x in _column(label_rows, *id_names)]
    lval = _floats(_column(label_rows, *label_names), "label")

    if len(set(pid)) != len(pid):
        dupes = sorted({i for i in pid if pid.count(i) > 1})[:5]
        raise EvaluationError(f"prediction has duplicate ids, e.g. {dupes}")
    by_id = dict(zip(pid, pscore))
    missing = [i for i in lid if i not in by_id]
    if missing:
        raise EvaluationError(
            f"prediction is missing {len(missing)} of {len(lid)} required ids, "
            f"e.g. {missing[:5]}")
    return np.asarray([by_id[i] for i in lid], dtype=float), lval


# --------------------------------------------------------------------------
# built-ins
# --------------------------------------------------------------------------
def auroc(prediction: Path, labels: Optional[Path], task=None) -> float:
    """Area under the ROC curve, joined on id. Labels must be binary 0/1."""
    if labels is None:
        raise EvaluationError("auroc needs a labels file")
    y_score, y_true = _align(
        _read_rows(prediction), _read_rows(labels),
        ("id", "resid", "sequence_id", "index"),
        ("score", "prediction", "probability", "prob", "pred"),
        ("label", "y", "target", "truth"),
    )
    uniq = set(np.unique(y_true).tolist())
    if not uniq <= {0.0, 1.0}:
        raise EvaluationError(f"auroc needs binary labels, found values {sorted(uniq)[:5]}")
    n_pos = float((y_true == 1).sum())
    n_neg = float((y_true == 0).sum())
    if n_pos == 0 or n_neg == 0:
        raise EvaluationError("auroc needs both classes present in the labels")
    ranks = _rankdata(y_score)
    return float((ranks[y_true == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def rmse(prediction: Path, labels: Optional[Path], task=None) -> float:
    """Root mean squared error against continuous labels, joined on id."""
    if labels is None:
        raise EvaluationError("rmse needs a labels file")
    y_pred, y_true = _align(
        _read_rows(prediction), _read_rows(labels),
        ("id", "resid", "sequence_id", "index"),
        ("score", "prediction", "value", "pred"),
        ("label", "y", "target", "truth", "value"),
    )
    return float(np.sqrt(((y_pred - y_true) ** 2).mean()))


def accuracy(prediction: Path, labels: Optional[Path], task=None) -> float:
    """Fraction of ids whose predicted class equals the label, joined on id."""
    if labels is None:
        raise EvaluationError("accuracy needs a labels file")
    y_pred, y_true = _align(
        _read_rows(prediction), _read_rows(labels),
        ("id", "resid", "sequence_id", "index"),
        ("score", "prediction", "class", "pred", "label"),
        ("label", "y", "target", "truth"),
    )
    return float((y_pred == y_true).mean())


def scalar(prediction: Path, labels: Optional[Path], task=None) -> float:
    """One number out of a free-form output file — the ``reproduce`` grader.

    Prefers an explicit ``<metric>=<value>`` (or ``<metric>: <value>``) line, so a task
    gets the number it asked for rather than whatever happened to be printed last.
    """
    try:
        text = prediction.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise EvaluationError(f"cannot read {prediction.name}: {exc}") from exc
    metric = getattr(getattr(task, "evaluation", None), "metric", "") or ""
    if metric:
        m = re.search(rf"\b{re.escape(metric)}\s*[=:]\s*({_NUM})", text, re.I)
        if m:
            return float(m.group(1))
    nums = re.findall(_NUM, text)
    if not nums:
        raise EvaluationError(
            f"no number found in {prediction.name}"
            + (f" (looked for '{metric}=<value>' first)" if metric else ""))
    if len(nums) > 1 and metric:
        raise EvaluationError(
            f"{prediction.name} has {len(nums)} numbers and none is labelled "
            f"'{metric}=' — refusing to guess which one is the answer")
    return float(nums[-1])


BUILTINS = {
    "auroc": auroc,
    "rmse": rmse,
    "accuracy": accuracy,
    "scalar": scalar,
}


def get(name: str):
    """Resolve an evaluator name: a built-in, or ``file:<path>`` exposing ``evaluate``."""
    if name.startswith("file:"):
        path = Path(name[5:])
        if not path.exists():
            raise EvaluationError(f"evaluator script not found: {path}")
        import importlib.util

        spec = importlib.util.spec_from_file_location(f"_eval_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, "evaluate", None)
        if fn is None:
            raise EvaluationError(f"{path} defines no evaluate(prediction, labels, task)")
        return fn
    fn = BUILTINS.get(name)
    if fn is None:
        raise EvaluationError(
            f"unknown evaluator {name!r}; built-ins are {sorted(BUILTINS)} "
            f"(or use 'file:<path>')")
    return fn
