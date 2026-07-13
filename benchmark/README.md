# Lazarus Benchmark — scope

*Measure how much published computational-biology software has decayed, and how much of it an agent can bring back — honestly, at scale. The runs populate the [registry](../registry/); the populated registry becomes the paper.*

## Two headline numbers (from the same runs)
1. **Decay rate** — of a sample of published comp-bio methods, what fraction *don't run today* out of the box. (The "half-life of computational biology software" finding — independent of Lazarus.)
2. **Revival rate** — of the dead ones, what fraction **Lazarus** revives autonomously (passes a falsifiable sanity check), and of those, how many **reproduce the paper's number**.

## Locked decisions (2026-07-11)
- **Corpus:** *hybrid* — a small **curated pilot** to harden the harness + get a first number, then a **principled random sample** (defined frame, random draw, report on all) for the publishable rate.
- **Domain:** computational biology only (tight frame = stronger paper).
- **Pilot size:** ~10–12 repos.

## Metrics (per repo)
`outcome` (reason code) · `turns` · `wall_clock_s` · `api_cost` · `naive_runs` (baseline) · `sanity{metric,threshold,measured}` · `reproduced{metric,reported,measured}` · `contract` (if success) · `scout_plan` · `notes`.

### Reason-code taxonomy (the failures ARE the science)
Success: `reproduced` · `revived` · `runs-unverified`
Failure: `weights-gone` · `data-gated` · `hardware-incompatible` · `unresolvable-deps` · `license-blocked` · `budget-exceeded`

The *distribution* of failure reasons is itself a result — e.g. "*N%* of dead repos fail because the **weights** vanished, not the code," which nobody has measured.

### The baseline (`naive_runs`) — design item
Decay rate needs a fair "does it run without the agent?" measurement. Proposed protocol: a fixed, agent-free attempt in a clean container (follow the README install, run the shipped example, cap at *K* minutes). Needs to be defined precisely and applied identically to every repo. **Open.**

## Corpus

### Pilot (curated, vetted before running)
~10–12 comp-bio repos chosen to span outcomes (some revive, some honest failures), **excluding** the six already revived (those seed the registry but don't count toward the measured rate). Each candidate is vetted for: public repo, stale, weights downloadable (or knowably-gone), a small checkable sanity input, and runnable on our hardware — same checklist we used for Basset/DiffDock.

**Candidate shortlist (to vet — states are hypotheses until checked):**

| Candidate | Repo | Area | Why / expected signal |
|---|---|---|---|
| DeepFRI | flatironinstitute/DeepFRI | protein function ← structure | TF ~2021, weights shipped |
| ProteinBERT | nadavbra/protein_bert | protein LM | TF/Keras, weights on HF |
| trRosetta | gjoni/trRosetta | contact/structure | TF 2019, weights available |
| EquiBind | HannesStark/EquiBind | blind docking | PyTorch/PyG, ICML'22 |
| EquiDock | octavian-ganea/equidock_public | protein–protein docking | PyG |
| GraphDTA | thinng/GraphDTA | drug–target affinity | PyG, older |
| DeepDTA | hkmztrk/DeepDTA | drug–target affinity | Keras 2018 |
| DeepPurpose | kexinhuang12345/DeepPurpose | drug–target | PyTorch |
| TAPE | songlab-cal/tape | protein representation | PyTorch, stale |
| DanQ | uci-cbcl/DanQ | genomics (regulatory) | Theano/Keras — **weights likely gone** (honest `weights-gone`) |
| Basenji | calico/basenji | genomics | TF, Basset's successor |
| scGen | theislab/scgen | single-cell | old TF |
| UniRep | churchlab/UniRep | protein representation | TF1 — likely hard |

Vet down to ~10–12; deliberately keep 2–3 with expected honest failures so the rate is real.

### Principled sample (for the paper — defined after the pilot)
Define a **sampling frame** — comp-bio papers in a set of venues over a year range (candidates: *Bioinformatics*, *Nature Methods*, *PLOS Comp Biol*, and the ML-for-bio tracks) with a linked public GitHub repo — then draw a **random** sample and attempt **all** of them (brutal failures included). Frame + N finalised after the pilot proves the harness.

## Harness to build (Phase 1)
`benchmark/run.py` — given a repo URL (or the pilot list):
- run `lazarus resurrect --yes <url>` under hard caps: `--max-turns`, a wall-clock timeout, and a per-repo cost ceiling;
- capture the metrics + reason code (agent-reported + a classifier over the final state);
- **resumable** remote/GPU execution (Bertha dropped mid-DiffDock once — snapshots + resume must be first-class);
- on success, auto-write a `registry/entries/*.yaml` and refresh the index;
- append a row to `benchmark/results.json`; a separate `benchmark/report.py` renders the table + figures.

**Gaps to close along the way:** cost/token capture per run; a defined `naive_runs` baseline; publishing revived **images** to a public registry (GHCR) so registry entries become fully runnable, not just rebuildable.

## Staging
1. **Harness** (`run.py` + results schema + registry auto-landing + resumability) — test on 2–3 vetted repos.
2. **Vet the pilot shortlist** → final ~10–12.
3. **Pilot run** → first decay + revival numbers; iterate the harness.
4. **Principled sample** (frame + random draw) → the publishable rate + figures.
5. **Write-up.**

## Paper framing (working)
- **Title:** *The half-life of computational biology software — and an agent that reverses it.*
- **Contributions:** (1) a measured decay rate; (2) a benchmark + rate for autonomous revival; (3) an open, reproducible harness + a public registry of revived tools; (4) a failure taxonomy.
- **Venue:** an ML-for-science / reproducibility workshop first (fast signal), then *Bioinformatics* / *GigaScience* / *PLOS Comp Biol* (repro-friendly).

## Open questions
- Exact `naive_runs` baseline protocol.
- Cost/token capture from the Agent SDK per run.
- Publishing images to GHCR (needed for fully-runnable registry entries).
- Final venue/year frame for the principled sample.
