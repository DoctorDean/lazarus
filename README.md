<p align="center">
  <img src="https://raw.githubusercontent.com/DoctorDean/lazarus/main/lazarus.png" width="440" alt="Lazarus — resurrecting a dead repo" />
</p>

<h1 align="center">Lazarus</h1>

<p align="center"><em>Turn dead research code into a callable pipeline component — and give the revival back.</em></p>

<p align="center">
  🏆 <strong>Winner — Build track, Claude Science hackathon</strong> · July 2026
</p>

<p align="center">
  <a href="https://pypi.org/project/lazarus-bio/"><img src="https://img.shields.io/pypi/v/lazarus-bio?color=0c8f6e" alt="PyPI" /></a>
  <a href="https://doctordean.github.io/lazarus/"><img src="https://img.shields.io/badge/docs-github.io-0c8f6e" alt="Docs" /></a>
  <a href="https://colab.research.google.com/github/DoctorDean/lazarus/blob/main/notebooks/Lazarus_Democratizing_Dead_SOTA.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" /></a>
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT" />
</p>

<p align="center"><em>New here? <a href="notebooks/Lazarus_Democratizing_Dead_SOTA.ipynb">Open the notebook in Colab</a> — a 2-minute, zero-setup tour (no Docker, no GPU): run the dependency pinner live, inspect the revived tools, and see the binder-triage result rendered in 3D.</em></p>

---

## The wall

Computational science has a reproducibility problem. A huge fraction of published methods
are **open, cited, and unrunnable** within a few years: the repo is stale, wired to a stack
that no longer resolves, and the real capability is buried in scripts with no API. If you're
on a small, budget-constrained ML-for-biology team, you hit this constantly — the exact
method you need exists, but getting it to run costs days you don't have, so it gets abandoned.

## What Lazarus does

Lazarus is an agent that **revives** dead research code, lets you **compose** the revivals
into pipelines, and **gives the fixes back** to the community.

1. **Revive** — point it at a **bare GitHub URL**. Lazarus reads the repo and the paper the
   way a newcomer would and **writes its own goal and sanity check**, then runs a
   build → execute → read-traceback → repair loop in a sandbox. Pin dependencies to the
   commit era, resolve the binary chain, locate the real capability, and emit a fixed
   **integration contract**: an importable module, a CLI, a pinned container, and a smoke
   test that proves it runs on a fresh input and passes the sanity check it defined.
2. **Compose** — because every revival emits the *same* contract, a revived tool is a
   composable **brick**. Wire bricks from any domain/language/era into a pipeline with a
   small YAML; one command runs them, passing artifacts between steps (local / remote / GPU).
3. **Give back** — the fixes Lazarus finds (rotted URLs, broken paths, a 15-year-old
   undefined-behavior bug) become maintainer-ready **pull requests** with CI, so the method
   can't silently rot again.

## Proof — four dead repos, resurrected autonomously

Each revived from its own dead environment using only general heuristics (no repo-specific
notes), each emitting a callable package that passes its **own smoke test standalone**:

| Repo | Flavor | Turns | Result on `4ZQK_A` |
|---|---|:--:|---|
| **MaSIF-site** ([LPDI-EPFL/masif](https://github.com/LPDI-EPFL/masif)) | Py3.6 · TF 1.12 · surface + MSMS/APBS (revive-and-carve) | 18 | interaction site, **ROC-AUC 0.9137** |
| **ScanNet** ([jertubiana/ScanNet](https://github.com/jertubiana/ScanNet)) | Py3.6 · TF 1.14 · Keras (revive-and-carve) | 19 | binding site, **ROC-AUC 0.9233** |
| **dMaSIF** ([FreyrS/dMaSIF](https://github.com/FreyrS/dMaSIF)) | Py3.6 · torch cu111 · PyKeOps · **GPU, built from scratch** | 51 | binding site, **ROC-AUC 0.8390** |
| **fpocket** ([2010 SourceForge](https://fpocket.sourceforge.net/)) | **2010 C**, built on modern GCC — a different flavor entirely | 32 | 3 druggable pockets |

The dMaSIF run built a whole CUDA/KeOps GPU environment from a bare image and **patched a
source bug to unlock GPU execution the original forced to CPU**. The fpocket run fought a
SourceForge download interstitial, a modern-`ld` link-order break, and a **15-year-old
overlapping-`sprintf` undefined-behavior bug** that modern glibc exposed. Three genuinely
different resurrection flavors — TF/CUDA/C.

**Three-way head-to-head** (the three site predictors, scored by one script on identical
PD-L1 residue labels): **ScanNet 0.915 · dMaSIF 0.854 · MaSIF 0.823**. All localize the
interface (a **13-residue consensus core**); the two *surface* methods (MaSIF & dMaSIF)
agree most (Spearman ρ 0.70). Details: [`analysis/RESULTS.md`](analysis/RESULTS.md).

## Point it at a URL — it writes its own plan

You don't hand Lazarus a goal; you hand it a link. A web-enabled **Scout** reads the repo
and paper (and *only* those — never your notes) and drafts the whole plan: the capability to
revive, a base image, and a **falsifiable sanity check**. Then it pauses for your OK before
spending a turn.

```bash
lazarus resurrect https://github.com/jertubiana/ScanNet
```

Run cold against ScanNet with **no hints**, the Scout reconstructed — from the URL alone — a
plan matching the one a human expert hand-wrote after days of work:

| | Human, after days of setup | Scout, from the URL alone |
|---|---|---|
| Capability | per-residue binding-site probabilities | ✅ same |
| Test input | 4ZQK chain A (PD-L1) | ✅ same |
| Sanity check | ROC-AUC ≥ 0.70 vs the 5 Å interface | ✅ **identical** |
| Base image | *(supplied by hand)* | ✅ found the real `jertubiana/scannet` on Docker Hub |
| Known traps | issues #14 & #15 (hand-noted) | ✅ **surfaced both unaided** — the two we later fixed upstream |

That's the democratization step: the expert judgment of *what "revived" even means* becomes
something you get from pasting a link.

**Then we pointed it at a repo we'd never touched, in a different field entirely.** From just
`github.com/davek44/Basset` — a 2016 **Lua Torch7** genomics CNN (chromatin accessibility from DNA
sequence) — the Scout planned it and the agent revived it end to end. Along the way it cleared a
*new* class of decay (the README's 2016 Docker image ships a manifest modern Docker refuses to pull
— converted with `skopeo`), and caught a **silent scientific-correctness bug**: the naive run scored
mean AUROC **0.675**, but the agent traced it to hg19's soft-masked lowercase bases falling through
Basset's uppercase-only one-hot encoder, patched it, and **reproduced the paper — mean AUROC 0.8944
vs 0.895** across all 164 cell types. A fifth brick, a new domain (genomics, not protein surfaces),
a fourth dead framework — from a link. Details: [`docs/CHALLENGES.md`](docs/CHALLENGES.md) §5.

**And the one that shows the *integrity* of the sanity check:** from `github.com/gcorso/DiffDock`
— the ICLR-2023 diffusion **molecular-docking** model, ~2 years stale — the Scout revived it on
GPU. Its shipped example is a hard case (top-1 ~5 Å, under DiffDock's own < 2 Å bar), so rather
than fake a pass, Lazarus docked **8 complexes from DiffDock's own test set**, **reproduced its
~40 % top-1 success rate**, and found a rock-solid hero case (**6MOA: RMSD 0.35 Å** — the predicted
pose sitting on the crystal ligand). It refused to ship a green checkmark it hadn't earned. Details:
[`docs/CHALLENGES.md`](docs/CHALLENGES.md) §6.

## Compose — an in-silico pipeline from revived bricks

`examples/pipelines/binder_triage.yaml` assembles **methods that were each individually
unrunnable a week ago** into one binder-triage pipeline:

```
structure ─▶ ScanNet ─┐
          ─▶ dMaSIF ──┼─▶ consensus ─▶ interface residues that also line a druggable pocket
          ─▶ fpocket ─┘
```

```bash
lazarus run examples/pipelines/binder_triage.yaml \
  --input structure=4ZQK.pdb \
  --registry examples --registry components \
  --docker-host ssh://you@your-x86-gpu-box
```

Run live on PD-L1, it concluded: **27 interface residues** (115, 123, 56, 121, 113…), but
**0 druggable pockets** → *"the interface is clearly localized but not a druggable small-
molecule pocket — a flat protein-protein interface, i.e. an antibody/biologic target."*
That's textbook immuno-oncology (PD-1/PD-L1 *is* an antibody target), reproduced from dead
code. Sample output: [`examples/pipelines/sample_output_4ZQK/`](examples/pipelines/sample_output_4ZQK/).

## Give back

For the genuinely-abandoned repos, Lazarus prepares maintainer-ready PRs — the real fix
plus a **CI smoke test** so it can't silently rot again:

- **MaSIF — [PR #93](https://github.com/LPDI-EPFL/masif/pull/93)** — the rotted PDB download,
  fixed (direct RCSB fetch); verified to revive the built-in flow at ROC-AUC 0.9137. →
  [`giveback/masif/`](giveback/masif/)
- **ScanNet — [PR #16](https://github.com/jertubiana/ScanNet/pull/16)** — `library_folder=''`
  made to auto-detect the repo root; verified. → [`giveback/scannet/`](giveback/scannet/)

(dMaSIF is skipped — CC BY-NC-ND, no-derivatives; fpocket's upstream is alive.)

## Reproduces the paper

A smoke test proves a method *runs*; a benchmark proves it's *the method*. Lazarus re-ran
MaSIF-site on its own **transient PPI benchmark** — through the built-in download that
give-back [PR #93](https://github.com/LPDI-EPFL/masif/pull/93) revived — and matched the published number:

| Metric | Paper (Gainza et al. 2020, n=59) | Lazarus (n=15 slice) |
|---|:--:|:--:|
| median per-structure ROC-AUC | **0.85** | **0.82** → **reproduced** (±0.05) |

Every revival can carry this: the contract's `benchmark` field emits a
[`REPRODUCE.md`](examples/masif_site_contract/REPRODUCE.md) certificate with a PASS/OFF
verdict — the trust layer that turns a resurrection into something a team will actually adopt.

## Measured — most of these repos are dead, and Lazarus revived them all

The hero repos above are anecdotes. To test the thesis honestly we drew a **principled,
seeded random sample** — 20 tools published in *Bioinformatics* (2018–2021) — and ran two
passes over each: an **agent-free baseline** (does it still run today?) and the **full
Lazarus harness** (can the agent revive it?), with every verdict independently re-verified.

| | Result | 95% CI |
|---|:--:|:--:|
| **Ran on its own today**, agent-free | **3 / 20** — so **85% are dead** | 64–95% |
| **Revived by Lazarus**, of the dead ones | **17 / 17 → 100%** | 82–100% |
| Reproduced the paper's own reported metric | **5 / 20** | |

85% of a random slice of recent, peer-reviewed computational biology **won't install or run**
a few years on. Lazarus brought back **every** dead repo in the sample — 20 / 20 overall —
and 5 matched the original paper's numbers. Nothing here is cherry-picked: the frame, the
seed, the per-repo outcomes, and the runnable harness are all in [`benchmark/`](benchmark/)
(`benchmark/report.py` regenerates the table with confidence intervals).

## How it works — five organs

| Organ | Role |
|---|---|
| **Scout** | Reads a bare repo URL + its paper (web-enabled, but blind to your notes) and drafts the resurrection plan: capability, base image, and a falsifiable sanity check — so a revival starts from a link, not a hand-written goal. |
| **Sandbox** | Disposable container (CPU or GPU); expensive successes are snapshotted so a later failure never re-pays the build. |
| **Commit-era pinner** | Reconstructs the dependency universe as it was on the repo's last commit — the reasoning that beat the cu111/KeOps/`cppyy` tangle. |
| **Repair loop** | build → run → read traceback → patch → retry, bounded, isolated to the container. |
| **Capability locator** | Finds where "input → the famous output" happens and carves the minimal path to it. |
| **Contract emitter** | Module + CLI + pinned container + smoke test — CPU or GPU, verified callable on its own. |

## Runs on a laptop, executes anywhere

Lazarus runs on your machine; *where it executes* is pluggable via one flag — a local
container, a remote x86 box, a **cloud VM**, or a **GPU rental** — for methods (like MaSIF's
MSMS or dMaSIF's CUDA) whose binaries need hardware laptop emulation can't provide. The
agent's tools and the emitted `predict.py` both run against whatever `--docker-host` /
`DOCKER_HOST` points at, so the whole chain is host-agnostic.

## The registry — pull a revived tool

Every revival lands in a living registry, so you don't have to re-resurrect what someone
already did. Browse it and pull any tool's contract — an importable module, a CLI, a pinned
container, and the smoke test that proves it runs:

```bash
lazarus registry                              # list the revived tools
lazarus pull scannet_ppi_binding_sites        # fetch its contract bundle
```

Six tools are in today — **MaSIF-site, ScanNet, dMaSIF, fpocket, Basset, DiffDock** — each a
callable brick backed by a pinned container image on **GHCR** (see [`docs/IMAGES.md`](docs/IMAGES.md)
to run one). Adding a tool is a pull request: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Try it — the dashboard

A public "try it" surface: search a GitHub repo, watch it come back to life, browse the registry.

```bash
uvicorn demo.dashboard.app:app --port 8080    # → http://localhost:8080
```

## Quickstart

```bash
pip install lazarus-bio                      # the tooling: pinner, compose, contracts
pip install "lazarus-bio[agent]"             # + the autonomous revive loop & Scout (Python ≥ 3.10 + Docker)
# or, to hack on Lazarus itself:
#   git clone https://github.com/DoctorDean/lazarus && cd lazarus
#   pip install -e ".[dev,agent]"

# commit-era dependency pinning — no repo execution required
lazarus pin --date 2019-01-01 tensorflow numpy scipy
#   tensorflow==1.12.0   (matches MaSIF's real Dockerfile, not its README)

# resurrect straight from a URL — the Scout writes the goal + picks the image,
# then pauses for your OK before spending compute (needs Docker + Claude auth)
lazarus resurrect https://github.com/jertubiana/ScanNet

# …or drive it by hand with an explicit image + goal (both override the Scout)
lazarus resurrect --image pablogainza/masif:latest --workdir /masif \
  --goal-file examples/masif_site_goal.txt --keep

# browse & pull from the registry of already-revived tools
lazarus registry
lazarus pull scannet_ppi_binding_sites

# compose revived components into a pipeline
lazarus run examples/pipelines/binder_triage.yaml --input structure=4ZQK.pdb \
  --registry examples --registry components
```

**Auth:** Lazarus drives Claude via the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python).
Log in the `claude` CLI (subscription) or put `ANTHROPIC_API_KEY=...` in a gitignored `.env`.

## Status

Working today: **Scout** (URL → resurrection plan) · pinner · Docker sandbox (local + `ssh://`
remote + `--gpus`) · autonomous repair loop · capability locator · contract emitter (GPU-aware,
with reproduction certificates) · **Lazarus Compose** · a **registry** of revived tools · a
public **dashboard**. All three pillars landed — the curated hero set of **six** dead repos
revived (protein + genomics + molecular docking), a three-way method comparison, a live
binder-triage pipeline, reproduced paper benchmarks, and two give-back PRs — plus a
**principled N=20 benchmark** (85% of the sample dead, 100% of the dead revived; see
[`benchmark/`](benchmark/)). 66 passing tests, published to PyPI (`pip install lazarus-bio`).

**Contributions welcome** — add a repo, curate a registry entry, or file a revival that failed.
Start at [CONTRIBUTING.md](CONTRIBUTING.md). Development happens on the `next` branch.

**Two front doors:** a [zero-setup Colab notebook](notebooks/Lazarus_Democratizing_Dead_SOTA.ipynb)
for newcomers (no Docker/GPU — pinner live + the result rendered in 3D), and the
[interactive dashboard](demo/dashboard/) — search a repo, watch it come back to life, and
browse the registry.

## License

MIT — see [LICENSE](LICENSE).
