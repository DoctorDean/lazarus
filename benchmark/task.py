#!/usr/bin/env python3
"""Benchmark task specs — the harness's own definition of "solved".

The registry-building harness (``run.py``) lets the *agent* define success: the Scout
emits a falsifiable sanity metric and threshold, and ``verify_smoke`` re-runs the agent's
own smoke command. That's the right control for a registry — it catches an agent
self-awarding a pass — but it cannot rank *different* agents, because each submission
would set its own difficulty (nothing stops ``metric=exit_code, threshold=0``).

A benchmark task inverts that. The harness supplies a fixed input, holds the ground
truth, and grades the submission's *output artifact* with its own evaluator. The agent
never writes its own exam.

Two kinds, per benchmark/LEADERBOARD_SCOPE.md:

``predict``    the harness holds hidden labels and scores predictions against them.
               Strong: ground truth is private. Requires an input, an output schema,
               labels, and an explicit metric direction.

               A `predict` task may instead be **self-verifying** (``self_verifying:
               true``), meaning the answer is checkable from the input alone rather than
               against a stored label — a linear solve graded by its residual, a structure
               graded by its energy, a route graded by whether it closes. These are the
               strongest tasks available: there is no answer key to leak, so they cannot
               be contaminated, and anyone can recompute the score from the input.
``reproduce``  the submission reports the paper's headline number and the harness
               compares it to the published value within a relative band. Broad, but
               weaker — the target is printed in the paper.

Tasks are **pinned**, never floating. Upstream moves, and in our case we moved it ourselves
(the give-back PRs to MaSIF and ScanNet); a task that clones HEAD is measuring a target we
changed. A pin comes in two forms and validation requires exactly one:

``commit``                          a git SHA — for anything on GitHub.
``artifact_url`` + ``artifact_sha256``  a content-addressed download — for the large share
                                    of dead science that was never in git at all (fpocket
                                    is a 2010 SourceForge tarball; Basset was recovered
                                    from a 2016 Docker image). Requiring git would bias the
                                    benchmark toward modern, well-packaged code, inverting
                                    the very finding that packaging discipline rather than
                                    recoverability is what separates reviewed from
                                    unreviewed software. A sha256 is the *stronger* pin: it
                                    fixes bytes, where a git ref only names them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import yaml

KINDS = ("predict", "reproduce")
DIRECTIONS = ("higher", "lower")

# A git pin must look like an object id. Branch names and tags are rejected outright:
# they are exactly the moving targets this field exists to prevent.
_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class TaskError(ValueError):
    """A task spec is malformed. Raised at load time, never at scoring time."""


@dataclass
class Caps:
    """Identical for every submission; enforced by the harness, not self-reported."""

    turns: int = 90
    wall_clock_s: int = 5400
    cost_usd: float = 10.0


@dataclass
class Evaluation:
    """How the harness grades the submission's output. Harness-owned, not agent-owned."""

    evaluator: str                       # built-in name (see evaluators.BUILTINS) or "file:<path>"
    metric: str                          # what the evaluator returns, e.g. "auroc"
    threshold: Optional[float] = None    # predict: the bar to clear
    direction: str = ""                  # predict: "higher" | "lower" — never inferred
    labels: str = ""                     # predict: path to ground truth, relative to the task dir
    self_verifying: bool = False         # predict: ground truth is computed, not stored (below)
    reported: Optional[float] = None     # reproduce: the paper's published value
    rel_tol: float = 0.15                # reproduce: relative band (matches run.REPRODUCE_REL_TOL)


@dataclass
class Task:
    id: str
    repo_url: str
    kind: str
    capability: str
    evaluation: Evaluation
    commit: str = ""                     # git pin (exactly one pin required)
    artifact_url: str = ""               # non-git pin: content-addressed download
    artifact_sha256: str = ""
    paper: str = ""
    domain: str = ""                     # cross-domain scope: track the field per task
    input_path: str = ""                 # predict: harness-supplied input, relative to the task dir
    input_sha256: str = ""
    output_path: str = "prediction.csv"  # what the submission must write into --out
    output_schema: list = field(default_factory=list)
    caps: Caps = field(default_factory=Caps)
    split: str = "dev"                   # dev (public) | test (labels withheld)
    notes: str = ""
    _dir: Optional[Path] = field(default=None, repr=False, compare=False)

    # ---- paths (resolved against the task's own directory) ----
    def _resolve(self, rel: str) -> Optional[Path]:
        if not rel:
            return None
        p = Path(rel)
        return p if p.is_absolute() or self._dir is None else self._dir / p

    @property
    def input_file(self) -> Optional[Path]:
        """The task's input. May be a single file or a directory of them — several tasks
        need more than one (a receptor *and* a ligand SMILES; a matrix *and* a rhs)."""
        return self._resolve(self.input_path)

    @property
    def pin_kind(self) -> str:
        return "git" if self.commit else "artifact"

    @property
    def pin(self) -> str:
        """Short, display-friendly form of whichever pin this task carries."""
        return self.commit[:8] if self.commit else f"sha256:{self.artifact_sha256[:8]}"

    @property
    def labels_file(self) -> Optional[Path]:
        return self._resolve(self.evaluation.labels)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("_dir", None)
        return d

    # ---- validation ----
    def validate(self) -> "Task":
        """Fail loudly at load time on anything that would corrupt a score later."""
        e = self.evaluation
        if not self.id or not re.match(r"^[a-z0-9][a-z0-9._-]*$", self.id):
            raise TaskError(f"id must be a lowercase slug, got {self.id!r}")
        if not self.repo_url.startswith(("http://", "https://")):
            raise TaskError(f"{self.id}: repo_url must be a URL, got {self.repo_url!r}")
        has_git = bool(self.commit)
        has_artifact = bool(self.artifact_url or self.artifact_sha256)
        if has_git and has_artifact:
            raise TaskError(
                f"{self.id}: give exactly one pin — a git `commit` or an "
                f"`artifact_url` + `artifact_sha256`, not both")
        if not has_git and not has_artifact:
            raise TaskError(
                f"{self.id}: a pin is required — either a git `commit` or an "
                f"`artifact_url` + `artifact_sha256` for sources that were never in git")
        if has_git and not _SHA_RE.match(self.commit):
            raise TaskError(
                f"{self.id}: commit must be a pinned git SHA (>=7 hex chars), got "
                f"{self.commit!r}. Branches and tags move — including from our own "
                f"give-back PRs — which would silently change what the task measures.")
        if has_artifact:
            if not self.artifact_url.startswith(("http://", "https://")):
                raise TaskError(
                    f"{self.id}: artifact_url must be a URL, got {self.artifact_url!r}")
            if not _SHA256_RE.match(self.artifact_sha256 or ""):
                raise TaskError(
                    f"{self.id}: artifact_sha256 must be 64 hex chars (the whole point of "
                    f"an artifact pin is that the bytes are fixed), got "
                    f"{self.artifact_sha256!r}")
        if self.kind not in KINDS:
            raise TaskError(f"{self.id}: kind must be one of {KINDS}, got {self.kind!r}")
        if self.split not in ("dev", "test"):
            raise TaskError(f"{self.id}: split must be 'dev' or 'test', got {self.split!r}")
        if not e.evaluator:
            raise TaskError(f"{self.id}: evaluation.evaluator is required")
        if not e.metric:
            raise TaskError(f"{self.id}: evaluation.metric is required")
        if not self.output_path:
            raise TaskError(f"{self.id}: output_path is required — it's what gets graded")

        if self.kind == "predict":
            if e.threshold is None:
                raise TaskError(f"{self.id}: predict tasks need evaluation.threshold")
            if e.direction not in DIRECTIONS:
                raise TaskError(
                    f"{self.id}: predict tasks need an explicit evaluation.direction "
                    f"{DIRECTIONS}, got {e.direction!r}. Direction is never inferred from the "
                    f"metric name — guessing it is what produced false negatives in "
                    f"interpret_smoke.")
            if not self.input_path:
                raise TaskError(f"{self.id}: predict tasks need an input_path")
            if not e.labels and not e.self_verifying:
                raise TaskError(
                    f"{self.id}: predict tasks need evaluation.labels (ground truth), or "
                    f"self_verifying: true if the answer is checkable from the input alone")
            if e.labels and e.self_verifying:
                raise TaskError(
                    f"{self.id}: self_verifying tasks compute their own ground truth — "
                    f"drop evaluation.labels so there's one source of truth")
        else:  # reproduce
            if e.reported is None:
                raise TaskError(
                    f"{self.id}: reproduce tasks need evaluation.reported (the paper's value)")
            if not e.rel_tol or e.rel_tol <= 0:
                raise TaskError(f"{self.id}: reproduce tasks need a positive rel_tol")
        return self

    def check_files(self) -> "Task":
        """Confirm the data a task references is actually present.

        Separate from validate() so a *test*-split task can be loaded and listed on a
        machine that doesn't hold the withheld labels.
        """
        for label, p in (("input", self.input_file), ("labels", self.labels_file)):
            if p is not None and not p.exists():
                raise TaskError(f"{self.id}: {label} file not found: {p}")
        return self

    # ---- loading ----
    @classmethod
    def from_dict(cls, d: dict, *, base_dir: Optional[Path] = None) -> "Task":
        d = dict(d or {})
        ev = d.pop("evaluation", None)
        if not isinstance(ev, dict):
            raise TaskError(f"{d.get('id', '<no id>')}: an `evaluation:` block is required")
        caps = d.pop("caps", None) or {}
        unknown = set(d) - {f for f in cls.__dataclass_fields__ if not f.startswith("_")}
        if unknown:
            raise TaskError(f"{d.get('id', '<no id>')}: unknown task field(s): {sorted(unknown)}")
        try:
            task = cls(evaluation=Evaluation(**ev), caps=Caps(**caps), **d)
        except TypeError as exc:
            raise TaskError(f"{d.get('id', '<no id>')}: {exc}") from exc
        task._dir = base_dir
        return task.validate()

    @classmethod
    def from_yaml(cls, text: str, *, base_dir: Optional[Path] = None) -> "Task":
        return cls.from_dict(yaml.safe_load(text) or {}, base_dir=base_dir)


def load_task(path) -> Task:
    """Load one ``task.yaml``; relative data paths resolve against its directory."""
    p = Path(path)
    return Task.from_yaml(p.read_text(encoding="utf-8"), base_dir=p.parent)


def load_tasks(root, *, split: Optional[str] = None) -> list:
    """Load every ``task.yaml`` under ``root``, sorted by id. Optionally filter by split."""
    tasks = [load_task(p) for p in sorted(Path(root).rglob("task.yaml"))]
    if split:
        tasks = [t for t in tasks if t.split == split]
    ids = [t.id for t in tasks]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise TaskError(f"duplicate task id(s) under {root}: {dupes}")
    return tasks


def main(argv=None) -> int:
    """Validate and list a task tree — run this before committing new tasks.

        python benchmark/task.py --root benchmark/tasks
    """
    import argparse

    ap = argparse.ArgumentParser(description="validate benchmark task specs")
    ap.add_argument("--root", default="benchmark/tasks")
    ap.add_argument("--split", choices=("dev", "test"))
    ap.add_argument("--no-files", action="store_true",
                    help="skip the data-file check (for a test split whose labels are withheld)")
    args = ap.parse_args(argv)

    try:
        tasks = load_tasks(args.root, split=args.split)
    except TaskError as exc:
        print(f"INVALID: {exc}")
        return 1
    if not tasks:
        print(f"no tasks found under {args.root}")
        return 1

    bad = 0
    for t in tasks:
        note = ""
        if not args.no_files:
            try:
                t.check_files()
            except TaskError as exc:
                note, bad = f"  <-- {exc}", bad + 1
        e = t.evaluation
        crit = (f"{e.metric} {'≥' if e.direction == 'higher' else '≤'} {e.threshold}"
                if t.kind == "predict" else
                f"{e.metric} within ±{e.rel_tol:.0%} of {e.reported}")
        print(f"{t.split:<5} {t.id:<28} {t.kind:<9} {crit:<34} {t.pin:<15} "
              f"{t.domain or '-'}{note}")
    print(f"\n{len(tasks)} task(s), {bad} with missing data")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
