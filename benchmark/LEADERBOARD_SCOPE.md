# Scope — a public benchmark for reviving dead research code

*Roadmap Tier-1 "durable" track. Status: **P0 landed, P1 in progress** — the
task/evaluator/grading layer is built and tested; 5 of ~20 dev tasks converted, now cross-domain.*

**Settled:** the test split chases `predict` tasks with hidden labels, and scope is
**cross-domain** (not comp-bio only) — the generalisation result is the more interesting
claim and the v0.4 corpus already spans a dozen fields.

**The pitch:** *SWE-bench for resurrecting dead scientific software.* A frozen set of dead
repositories, a fixed success criterion per repo, and a submission format so any agent — not just
Lazarus — can be scored on how much science it brings back. It recruits the AI-agent community to
the problem, makes Lazarus the reference implementation rather than the only implementation, and
is a clean second paper off a corpus we have already built.

---

## 1. What already exists

More than half the instrument is built and battle-tested. This is not a from-scratch project.

| Piece | Where | State |
|---|---|---|
| Run harness | [`benchmark/run.py`](run.py) (510 ln) | Scout → resurrect under turn/time caps → classify → verify → append. Corpus-level resume (`already_done`), wall-clock watchdog with retried force-remove |
| Failure taxonomy | `run.py:36` `SUCCESS`/`FAILURE`/`INFRA`, `classify()` | Pure, unit-tested. 9 reason codes |
| Harness-owned reproduction test | `run.py:26` `reproduced_ok()` | 15% relative band, explicitly *not* the agent's self-declared tolerance |
| Independent verifier | `run.py:145` `interpret_smoke()` | Re-runs the emitted smoke; abstains (`None`) rather than guessing an unknown metric direction |
| Agent-free baseline | [`benchmark/baseline.py`](baseline.py) (296 ln) | Fixed no-repair protocol: clone → install from the repo's own files → run a shipped example, 30-min cap, stage+reason recorded |
| Sampling frames | `frame.py`, `frame_crossdomain.py`, `joss.py`, `crossref.py` | JOSS + Europe PMC + Crossref corpus builders |
| Reporting | `report.py` | Tables + figures |
| Results corpus | `results*.json` | **67 unique repos** attempted end-to-end |

**Measured on those 67 runs** — the numbers that make this affordable:

| | median | mean | max |
|---|---|---|---|
| API cost / repo | **$1.15** | $1.57 | $8.77 |
| Wall clock / repo | **17.6 min** | — | 11.7 h (a watchdog bug, since fixed) |
| Turns / repo | 26 | — | 60 |

Total spend across all 67: **$103.78**. Outcomes: 42 `revived`, 21 `reproduced`, 2
`budget-exceeded`, 1 `data-gated`, 1 `runs-unverified`.

---

## 2. What makes this a benchmark

What we have measures *Lazarus*. A leaderboard measures *anyone*. Five gaps, in order of how
hard they are to close.

### 2.1 The success criterion must move from the agent to the harness — **the central change**

Today the agent writes its own exam. The Scout emits a falsifiable `sanity_metric` + `threshold`
(genuinely clever for autonomy), and `verify_smoke` re-runs *the agent's own smoke command* in
*the agent's own image*. That's a real integrity control for a registry — it catches an agent
self-awarding a pass — but it cannot work for a leaderboard, because each submission would define
its own difficulty. Nothing stops a submission choosing `metric=exit_code, threshold=0`.

**The flip:** the benchmark supplies a fixed input and holds the ground truth. The submission
produces an *output artifact*; the harness scores that artifact with its own evaluator. The agent
never grades itself. This is exactly the SWE-bench `FAIL_TO_PASS` lesson.

Two task kinds cover our corpus:

- **`predict`** *(strong)* — harness gives a fixed input, holds hidden labels, runs its own
  evaluator over the submission's predictions. Ground truth is private.
- **`reproduce`** *(broad)* — submission emits the paper's headline scalar; harness compares to
  the published value via the existing `reproduced_ok()` band. Ground truth is public (it's in the
  paper), so it's weaker against gaming but applies to nearly everything.

Aim for `predict` wherever labels can be constructed; fall back to `reproduce`.

### 2.2 Our whole corpus is contaminated

Everything we have is burned as a test set, and it is worth being blunt about why:

- All **67 repo URLs and their outcomes** are committed in `results*.json`.
- The **registry publishes 25 working contracts** — base image, exact fix, sanity metric and
  threshold — and 23 pullable images on GHCR. For those tools, the answer is a `docker pull`.
- **We fixed some repos upstream.** MaSIF [PR #93](https://github.com/LPDI-EPFL/masif/pull/93)
  and ScanNet [PR #16](https://github.com/jertubiana/ScanNet/pull/16) mean `HEAD` may no longer be
  dead. A benchmark that clones `HEAD` is measuring a moving target we ourselves moved.

Consequences, non-negotiable:

1. **Pin every task to a commit SHA** that predates any Lazarus contribution. Tasks clone the SHA,
   never `HEAD`.
2. The 67 attempted repos and the 25 registry tools become the **public dev split**. They cannot
   be the test set.
3. The **test split must be freshly mined** and its labels never published.
4. **Rotate** the test set on a schedule; publish the retired set as dev.

### 2.3 There is no submission boundary

`run.py` imports `lazarus.scout` and `lazarus.resurrect` directly (`run.py:313-314, 324, 359, 385`).
It runs Lazarus; it cannot run anyone else's agent. A submission needs to be an opaque artifact.

**Proposed:** a submission is a Docker image with a fixed CLI.

```bash
docker run --rm --network=lazarus-bench \
  -v /task:/task:ro -v /out:/out \
  <submission-image> \
  --repo-url <url> --commit <sha> --task /task/task.yaml --out /out
```

It must write `/out/prediction.<ext>` (per the task's declared output schema) and may write
`/out/contract.yaml`. Everything else about how it works is its own business. The harness then
runs the task's evaluator against `/out` plus hidden labels.


### 2.4 The recorded results cannot supply the ground truth *(found during P1)*

The obvious shortcut for building tasks is to lift `reproduced_reported` out of
`results*.json` — 33 of the 67 runs have one. **It does not survive inspection.**

Of those 33, **20 are not paper numbers**: 14 are byte-identical to the run's own
`sanity_threshold`, and the rest are round self-consistency bars (`pearson_r = 1`,
`max_abs_diff = 0`, `reads_assigned = 100`). They are the agent's bar for itself, recorded
in a field named as if it came from the literature.

Promoting those to task targets would reintroduce the §2.1 problem through the data:
"reproduces the paper" would quietly mean "clears the bar the agent chose". The remaining
14 are *plausibly* paper-derived and still need a human to confirm each against the
source.

Consequences:

- `mine_tasks.py` classifies every candidate as `check-paper` (14), `agent-bar` (19) or
  `no-target` (34) and writes them to a **review manifest, never to a task**.
- Ground truth is hand-built or hand-verified per task. There is no bulk conversion, which
  is the single biggest driver of the P1 and P3 estimates.
- Tasks with *constructible* labels are worth far more than tasks with a quoted number,
  because the label can be rebuilt from a primary source and audited. All four dev tasks
  so far are of this kind.

### 2.5 The schema assumes git, and a lot of dead science isn't in git *(found during P1)*

`commit` is required, which quietly excludes any repo that isn't on GitHub. That's not an
edge case — it cuts out the era the benchmark most wants to cover. **fpocket**, one of the
25 registry tools, is a 2010 **SourceForge tarball**: no commits, no SHA, nothing to pin.
The same applies to supplementary ZIPs, institutional FTP, and the 2016 Docker image
Basset was recovered from.

Excluding them would bias the benchmark toward modern, well-packaged code — the exact
opposite of the v0.4 finding that *packaging discipline*, not recoverability, is what
separates reviewed from unreviewed software.

**Proposed:** make the pin polymorphic — either `commit` (git) **or** `artifact_url` +
`artifact_sha256` (a content-addressed download). Validation requires exactly one. Hashing
a tarball is in fact a *stronger* pin than a git SHA, since it fixes the bytes rather than
a mutable ref.

**Implemented** (`commit` XOR `artifact_url` + `artifact_sha256`). No task uses it yet:
fpocket's hash is not currently obtainable. SourceForge served an HTML interstitial to one download attempt and 2 bytes to
another — the same download evasion the original revival had to defeat. Building the schema
surface before a task can exercise it would be speculative, so this stays a design item
until the artifact can actually be captured (most likely from a mirror, or by recording the
hash during a live revival run).

---

## 3. Proposed task schema

```yaml
id: danq-2016
repo_url: https://github.com/uci-cbcl/DanQ
commit: 4d8f3b1...                  # frozen; predates any of our PRs
paper: 10.1093/nar/gkw226
capability: predict chromatin marks from a 1000 bp DNA sequence
kind: predict                       # predict | reproduce

input:
  path: inputs/danq_test.fa         # shipped with the task, content-addressed
  sha256: ...

output:
  path: prediction.csv
  schema: [sequence_id, target_index, score]

evaluation:                         # HARNESS-OWNED
  evaluator: evaluators/auroc.py    # runs in a fixed container
  labels: labels/danq_test.npy      # PRIVATE for the test split
  metric: auroc
  direction: higher                 # MANDATORY — never inferred from the name
  threshold: 0.85

caps: {turns: 90, wall_clock_s: 5400, cost_usd: 10}
```

`direction` is mandatory and explicit. `interpret_smoke`'s two-vocabulary heuristic exists because
guessing direction produced false negatives; in a task spec there is no reason to guess at all.

---

## 4. Scoring

| Metric | Definition | Role |
|---|---|---|
| **Revival rate** | fraction of tasks whose evaluator passes | **primary — the ranking** |
| Reproduction rate | of solved tasks, fraction within `reproduced_ok()` of the paper | secondary |
| Cost / solved task | median USD | reported, not ranked |
| Wall clock / solved task | median minutes | reported, not ranked |
| Failure profile | distribution over the 9 reason codes | diagnostic |

Row zero of every board is the **agent-free baseline** (`baseline.py`) — the "does it just run?"
floor. A submission that cannot beat it has demonstrated nothing. Publishing that floor is also
what keeps the decay claim honest.

Rank on revival rate alone. Cost is reported so an expensive win is visible without being
disqualifying.

---

## 5. Integrity

- **Network policy.** Repos need to fetch weights, so the network stays open — but the run happens
  behind a proxy that blocks `github.com/DoctorDean/lazarus`, `ghcr.io/doctordean/*`, and the
  `lazarus-bio` PyPI package. Otherwise a submission just pulls our answer. *(An allowlist would be
  stronger but would break the weight downloads that are half the difficulty.)*
- **Pinned SHAs** so upstream fixes — including ours — can't silently solve a task.
- **Hidden labels** for the test split; evaluators run maintainer-side.
- **Identical caps** for every submission, enforced by the harness, not self-reported.
- **Log retention** for every official run, so a result can be audited.

---

## 6. Infrastructure and cost

The numbers make this unusually cheap for a benchmark:

- A **50-task test sweep ≈ $60–80** in API cost (median $1.15/task) and **~15 GPU-hours**
  (median 17.6 min/task).
- None of the 67 runs so far needed a CUDA base image, but DiffDock/dMaSIF-class tasks will, so
  assume a GPU pool is required.

Three operating models:

| Model | Trust | Cost to us | Verdict |
|---|---|---|---|
| Self-run, submit logs | low | ~0 | fine for the dev split |
| Maintainer-run submissions | high | ~$80 + GPU-hours per submission | right for official test results |
| **Hybrid** | high where it matters | bounded | **recommended** — self-serve dev, maintainer-run test |

Bertha (one A4500) can host the dev split and a low submission volume. Anything beyond that needs
a cloud GPU pool and a queue.

---

## 7. Phasing

| Phase | Work | Rough size |
|---|---|---|
| **P0 ✅** | Task spec ([`task.py`](task.py)), evaluator interface ([`evaluators.py`](evaluators.py)), grading ([`score.py`](score.py)), the `apply_task_score` seam in `run.py`, a validator CLI, one real dev task, 28 tests | done |
| **P1** *(in progress)* | Convert ~20 of the 67 into a **public dev split**. Done: candidate miner + commit pinning (58 repos), 5 real `predict` tasks with constructible labels, 6 evaluators. Remaining: ~15 more tasks, each needing hand-built or hand-verified ground truth (see §2.4) | 3–5 days |
| **P2** | Submission boundary: containerised CLI, harness adapter, caps enforcement, Lazarus repackaged as the reference submission | 3–4 days |
| **P3** | Mine + freeze a **held-out test split** (~50 tasks, pinned SHAs, private labels) | 1–2 weeks, mostly compute + vetting |
| **P4** | Scoring, board rendering, public submission docs | 3–4 days |
| **P5** | Baseline numbers (agent-free floor + Lazarus reference), launch, paper draft | 1–2 weeks |

P0–P2 are the interesting engineering. P3 is the expensive part and the one that determines
whether the benchmark is credible.

---

## 8. Decisions

1. ~~**Task kind mix.**~~ **Settled: `predict` for the test split**, `reproduce` allowed in dev.
2. ~~**Domain scope.**~~ **Settled: cross-domain.** Every task carries a `domain` field so the
   board can be sliced by field, and so a submission that only handles bio is visible as such.
3. **Who runs official submissions.** Confirms whether P4 needs a queue and a budget.
4. **Test-set size.** 50 tasks ≈ $80/sweep. 100 doubles cost and roughly halves the noise on a
   single-point rate.
5. **Venue timing.** Freeze the test set before or after the workshop deadline? Freezing early
   makes the paper reproducible; freezing late buys more tasks.

---

## 9. Task patterns, ranked by how much they're worth *(learned in P1)*

Building the first five made the ordering obvious. Prefer the top of this list when
choosing what to convert next.

1. **Self-verifying** — the score is recomputed from the input (a residual, an energy, a
   constraint that either holds or doesn't). No answer key exists, so it cannot be leaked
   or contaminated, and anyone can audit the score. `pyamg-poisson-solve` is the model.
   **Cross-domain science is full of these** and they should dominate the held-out split.
2. **Constructible labels** — ground truth rebuilt from a primary source (interface
   residues from a deposited structure, a crystal ligand pose). Auditable and re-derivable,
   but the answer key ships with the task, so it only suits `dev` unless withheld.
3. **Paired tasks** — the same input, labels and threshold across two repos
   (`scannet-ppi-4zqk` / `dmasif-ppi-4zqk`). Worth building deliberately: they let the
   board attribute a difference to the method rather than to an easier task.
4. **Quoted paper numbers** (`reproduce`) — cheapest to write, weakest to trust, and
   §2.4 shows the recorded values can't be lifted without checking each against the source.
   Use only to fill gaps a constructible target can't reach.
