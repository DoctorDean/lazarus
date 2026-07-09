<p align="center">
  <img src="lazarus.png" width="440" alt="Lazarus — resurrecting a dead repo" />
</p>

<h1 align="center">Lazarus</h1>

<p align="center"><em>Turn dead research code into a callable pipeline component — and give the revival back.</em></p>

<p align="center">
  🧬 <strong>Build track</strong> · Built with <strong>Claude Science</strong> hackathon · July 2026
</p>

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

1. **Revive** — clone a dead repo, read the paper for intent, and run a
   build → execute → read-traceback → repair loop in a sandbox. Pin dependencies to the
   commit era, resolve the binary chain, locate the real capability, and emit a fixed
   **integration contract**: an importable module, a CLI, a pinned container, and a smoke
   test that proves it runs on a fresh input and passes a sanity check *you* define.
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

- **MaSIF #85** — the rotted PDB download, fixed (direct RCSB fetch); verified to revive the
  built-in flow at ROC-AUC 0.9137. → [`giveback/masif/`](giveback/masif/)
- **ScanNet #15** — `library_folder=''` made to auto-detect the repo root; verified. →
  [`giveback/scannet/`](giveback/scannet/)

(dMaSIF is skipped — CC BY-NC-ND, no-derivatives; fpocket's upstream is alive.)

## How it works — five organs

| Organ | Role |
|---|---|
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

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,agent]"     # agent extra needs Python ≥ 3.10

# commit-era dependency pinning — no repo execution required
lazarus pin --date 2019-01-01 tensorflow numpy scipy
#   tensorflow==1.12.0   (matches MaSIF's real Dockerfile, not its README)

# resurrect a capability in a sandbox (needs Docker + Claude auth)
lazarus resurrect --image pablogainza/masif:latest --workdir /masif \
  --goal-file examples/masif_site_goal.txt --keep

# compose revived components into a pipeline
lazarus run examples/pipelines/binder_triage.yaml --input structure=4ZQK.pdb \
  --registry examples --registry components
```

**Auth:** Lazarus drives Claude via the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python).
Log in the `claude` CLI (subscription) or put `ANTHROPIC_API_KEY=...` in a gitignored `.env`.

## Status

Working today: pinner · Docker sandbox (local + `ssh://` remote + `--gpus`) · autonomous
repair loop · capability locator · GPU-aware contract emitter · **Lazarus Compose** — with
**four** dead repos revived, a three-way method comparison, a live binder-triage pipeline,
two give-back PRs, and 44 passing tests.

## License

MIT — see [LICENSE](LICENSE).
