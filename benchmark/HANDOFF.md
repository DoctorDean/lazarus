# Handoff — benchmark / leaderboard work

State as of **2026-08-21**, branch `next` @ `8e0f092` (pushed; working tree clean; 160 tests
green on Python 3.9 and 3.12). Read this with [LEADERBOARD_SCOPE.md](LEADERBOARD_SCOPE.md),
which holds the full design and the phase table.

---

## 1. The one-paragraph version

Lazarus **v0.5.0 is released** (PyPI, tagged on merge commit `73bbfba`) — its headline is the
flagship pipeline where four resurrected tools converge on a real drug pocket in BRD2. All work
since then builds a **public benchmark** ("SWE-bench for resurrecting dead research software")
so *other people's* agents can be scored. The grading layer, a 7-task dev split and the
submission boundary are built and tested. The held-out test set — the thing that produces a
publishable number — does not exist yet.

## 2. The engine is untouched — keep it that way

`src/` and `pyproject.toml` are **byte-identical to the `v0.5.0` tag**. Verify before assuming:

```bash
git diff --stat v0.5.0..next -- src/ pyproject.toml     # must be empty
```

The wheel ships only `lazarus/`; nothing under `benchmark/` is packaged. Existing users of
`pip install lazarus-bio` are unaffected by any of this work.

**This is a constraint, not an accident.** The benchmark must not grow features into the
shipped package for its own convenience. It has already been tempting twice — see §6.

## 3. What is built

| Phase | Where | State |
|---|---|---|
| **P0** grading layer | `task.py`, `evaluators.py`, `score.py`, `run.py:apply_task_score` | done |
| **P1** dev split | `tasks/dev/*`, `mine_tasks.py`, `tasks/pins.json` | done (7 tasks, 4 domains) |
| **P2** submission boundary | `submission.py`, `SUBMISSION.md`, `reference/` | built, **never run end to end** |
| **P3** held-out test set | — | not started (the expensive phase) |
| **P4** scoring, board, proxy | — | not started |
| **P5** baseline + launch | — | not started |

The core idea of P0: **the harness owns the definition of "solved"**, not the agent. Previously
the Scout wrote its own sanity metric and `verify_smoke` re-ran the agent's own smoke command —
fine for cataloguing revivals, useless for ranking competitors.

Seven dev tasks, all `predict` except one:

```
deepdta-davis-ci              reproduce  concordance_index within ±3% of 0.878
diffdock-dock-6moa            predict    centroid_distance_A ≤ 2.0
dmasif-ppi-4zqk               predict    auroc ≥ 0.7
equibind-dock-6moa            predict    centroid_distance_A ≤ 2.0
pyamg-poisson-solve           predict    relative_residual ≤ 1e-08   (self-verifying)
pysrurgs-symbolic-regression  predict    r_squared ≥ 0.9
scannet-ppi-4zqk              predict    auroc ≥ 0.7
```

Every one was validated by grading real output through the task layer and reproducing the
number the original revival recorded (ScanNet 0.9233, dMaSIF 0.8390, DiffDock 0.223 Å,
EquiBind 0.838 Å). That agreement is the evidence the grading path is sound.

## 4. THE IMMEDIATE NEXT ACTION

**Run the reference submission once, end to end.** Everything in P2 is tested except whether
it works.

Target `scannet-ppi-4zqk` on Bertha (the A4500 box, `ssh dean@100.80.108.2`, reachable and
idle as of this writing). Its answer is known — 0.9233 against a 0.70 bar — so a pass is
unambiguous and a wrong number is diagnostic. Roughly 20–30 min and a couple of dollars of
API credit.

```bash
docker build -t lazarus-submission:0.5 benchmark/reference
# then drive it through the boundary (see SUBMISSION.md "Developing locally"),
# or invoke the wrapper directly with --task pointing at a STAGED (redacted) task dir
```

Integration points that have **never executed** — expect at least one to fail:

1. Docker socket / `DOCKER_HOST` plumbing from the submission container through to Bertha
2. the `claude` CLI actually present and working inside the submission image
3. `ANTHROPIC_API_KEY` reaching the resurrection loop
4. `bake_input_image()` producing a usable derived image
5. the agent genuinely writing conforming `resid,score` CSV rather than ScanNet's native format
6. the copy-out of `/lazarus_result/<output_path>` from the revival container

**Why before P3:** P3 is weeks of per-task ground-truth work that cannot be automated. Building
50 tasks against an unproven runner is how you find the chain is broken after the costly part
is sunk. One bug (§6.4) was already caught by inspection alone.

## 5. Settled decisions — do not re-litigate

- **Test split is `predict`-only.** A `reproduce` target is printed in the paper, so it can be
  looked up rather than computed. `reproduce` is dev-only; it exists for exactly one task.
- **Scope is cross-domain**, not comp-bio only. Every task carries a `domain` field.
- **Dev target cut from ~20 to ~9**, and it is a *coverage* target, not a count. Rationale in
  scope §10: nothing is computed from the dev split, so N there buys nothing. N matters for the
  **test** split, where a 90% rate at N=20 has a ±27pp Wilson CI vs ±12pp at N=100.
- **Ranking is revival rate.** Cost and wall clock are reported, never ranked.
- **Ungradable ≠ failed.** Runs the harness cannot grade stay out of the rate denominator, so a
  harness bug cannot deflate an agent's score.

## 6. Findings that shaped the design — know these before changing anything

**6.1 The recorded results cannot supply ground truth.** Of the 33 non-null
`reproduced_reported` values in `results*.json`, **20 are not paper numbers** — 14 byte-identical
to the run's own `sanity_threshold`, the rest round self-consistency bars (`pearson_r=1`,
`max_abs_diff=0`). They are the agent's bar for itself in a field named as if it came from the
literature. Lifting them would rebuild the exact self-grading problem P0 removes. Hence
`mine_tasks.py` classifies candidates (`check-paper` 14 / `agent-bar` 19 / `no-target` 34) and
writes a **review manifest, never a task**. Scope §2.4.

**6.2 Self-verifying tasks are the best kind.** Graded by recomputation from the input — a
residual, an energy, a constraint that holds or doesn't. No answer key exists, so they cannot
be leaked or contaminated, and anyone can audit the score. `pyamg-poisson-solve` is the model.
**Prefer these for the test split.** Ranking of patterns in scope §9.

**6.3 The schema assumed git.** fpocket is a 2010 SourceForge tarball; Basset came from a 2016
Docker image. Requiring a commit SHA would bias the benchmark toward modern, well-packaged code
— inverting the v0.4 finding. Fixed with a polymorphic pin (`commit` XOR `artifact_url` +
`artifact_sha256`). **No task uses the artifact path yet**: SourceForge blocks automated
downloads (HTML interstitial one way, 2 bytes the other), so fpocket's hash is unobtainable.
Do not invent one.

**6.4 Staging nearly handed over the answer.** `labels/` sits next to `input/` in a task dir,
and for a `reproduce` task `evaluation.reported` **is** the answer. `Task.public_view()` redacts
both; `stage_task()` byte-compares staged files against the label file and refuses to run on a
leak. A staging bug would invalidate every later score *while looking like an excellent
submission*.

**6.5 Turns and cost are not enforceable.** Against an opaque container only wall clock, memory,
CPU and network can be enforced. Turns and cost are internal to an agent. They are self-reported
metadata and **nothing may be ranked on them**.

**6.6 The wrapper's container boundary.** The revival happens in a *different* container from
the submission, so `/out` and `/task` do not exist where the agent works, and its tools
deliberately cannot write the host (`emit_contract` writes a contract bundle, nothing else). The
wrapper therefore bakes input into a derived image and copies the result back out. Both
wrapper-side — **this is the seam that keeps the benchmark out of `src/`.** If a future fix
tempts you toward teaching the Scout or the contract emitter about output schemas, that is a
product decision; raise it, don't do it quietly.

## 7. Traps

- **Never hand-type a commit SHA.** One plausible-but-fabricated EquiBind SHA got written during
  P1; a format regex accepts it. `tasks/pins.json` is the record of what was really resolved
  upstream, and a test asserts every task SHA matches it.
- **Check a new test actually fails without the fix.** Two tests in this work passed either way
  on first writing (the runner regressions; the goal-leak guard) and had to be reframed.
- **Calibrate a threshold against real data.** `pysrurgs` at 0.90 looked rigorous but a linear
  fit had to be measured (0.107) to know it discriminates. DeepDTA's default ±15% band would
  have admitted the paper's own weaker ablations.
- **`_force_remove` defaults to a 120 s budget.** Reusing it naively made the P2 suite take
  120 s; `run_submission` passes `kill_budget_s=30`.
- **GitHub API is 60/hr anonymous.** All 67 repos are already pinned in `tasks/pins.json`, so
  no lookups are needed. Optional `GITHUB_TOKEN` in `.env` (no scopes — every repo read is
  public) lifts it to 5000/hr, which P3 will want.

## 8. Open decisions for Dean

1. **Test set size** — 50 tasks ≈ $60–80 and ±17pp CI; 100 ≈ ±12pp.
2. **Where test ground truth comes from** — the real bottleneck. Self-verifying targets are
   preferred but each needs domain knowledge to define. Which fields, and any preferred sources?
3. **Who runs official submissions** — self-run + submitted logs (cheap, low trust),
   maintainer-run (trustworthy, ~$80 + GPU-hours per submission), or hybrid. Determines whether
   P4 needs a queue and a budget.

## 9. Also outstanding, outside the benchmark

The **reproducibility observatory** — the other Tier-1 roadmap track (continuous `decay-check`
over a large corpus plus a public dashboard) — has not been touched. It may matter more than the
leaderboard for actual adoption.

## 10. Resume commands

```bash
git -C . log --oneline -1                                  # expect 8e0f092
git diff --stat v0.5.0..next -- src/ pyproject.toml        # expect empty
.venv/bin/python -m pytest -q                              # expect 160 passed
.venv/bin/python benchmark/task.py --root benchmark/tasks  # list + validate the dev split
ssh dean@100.80.108.2 nvidia-smi                           # Bertha, for the live run
```
