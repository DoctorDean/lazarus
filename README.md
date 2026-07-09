<p align="center">
  <img src="lazarus.png" width="440" alt="Lazarus — resurrecting a dead repo" />
</p>

<h1 align="center">Lazarus</h1>

<p align="center"><em>Turn dead research code into a callable pipeline component.</em></p>

<p align="center">
  🧬 <strong>Build track</strong> · Built with <strong>Claude Science</strong> hackathon · July 2026
</p>

---

## The wall

If you're on a small, budget-constrained ML-for-biology team, you know this one.
You can't license Schrödinger or AlphaFold3, so you build on open-source repos and
papers — and the exact method you need is **published and open, but the repo is
three-to-five years stale**, thinly structured, and wired to a stack that no longer
resolves. Getting it to run at all — let alone calling it on *your* inputs inside a
workflow — costs days you don't have. So genuinely useful methods just get abandoned.

## What Lazarus does

Lazarus is an agent that clones such a repo, **reads the paper for intent**, and runs a
**build → execute → read-traceback → repair** loop in a sandbox. It pins dependencies to
the repo's commit era, resolves the external-binary chain, locates the real capability
buried in the scripts, and emits a fixed **integration contract**:

- a **pip-importable module**,
- a **CLI**,
- a **pinned container**, and
- a **smoke test** that proves the method runs on a fresh input and passes a sanity
  check *you* define.

Success is concrete: *import and run a method you couldn't execute this morning, on your
own structures, by the end of the week.*

## Proof — three dead repos, resurrected autonomously

Lazarus revived **three independent protein binding-site methods** — three eras, three
stacks (one a from-scratch GPU build) — each using only its general heuristics (no
repo-specific notes), each emitting a callable package that passes its **own smoke test
standalone** (no agent, pure Docker):

| Repo | Stack | Turns | Native output | Sanity on `4ZQK_A` | Package |
|---|---|:--:|---|---|:--:|
| **MaSIF-site** ([LPDI-EPFL/masif](https://github.com/LPDI-EPFL/masif)) | Py3.6 · TF 1.12 · surface + MSMS/APBS | 18 | per-vertex | **0.9137** *(vertex)* | ✅ |
| **ScanNet** ([jertubiana/ScanNet](https://github.com/jertubiana/ScanNet)) | Py3.6 · TF 1.14 · Keras · point-cloud | 19 | per-residue | **0.9233** *(residue)* | ✅ |
| **dMaSIF** ([FreyrS/dMaSIF](https://github.com/FreyrS/dMaSIF)) | Py3.6 · torch cu111 · PyKeOps · **GPU** | 51 | per-point | **0.8390** *(residue)* | ✅ |

The third is the stress test: **no docker image**, a CUDA-10 stack that won't run on
Ampere, missing weights, and a PyKeOps install that dead-ends on `cppyy`/glibc. Lazarus
built the whole cu111 + KeOps GPU environment from a bare image, found the real weights in
a community fork, and **patched a source bug to unlock GPU execution the original forced to
CPU**. (dMaSIF is CC BY-NC-ND — a research beat, not a shippable component.)

**Three-way head-to-head.** Scored by one script on identical residue labels (22 PD-L1
interface residues within 5 Å of PD-1): **ScanNet 0.915 · dMaSIF 0.854 · MaSIF 0.823**.
All three localize the interface (a **13-residue consensus core**), and the two *surface*
methods (MaSIF & its differentiable successor dMaSIF) agree most with each other (Spearman
ρ 0.70) — method family shows up in the numbers. Details:
[`analysis/RESULTS.md`](analysis/RESULTS.md).

📄 **The resurrection report** (visual — all three + the head-to-head) lives at
[`docs/resurrection_report.html`](docs/resurrection_report.html). The emitted packages are in
[`examples/masif_site_contract/`](examples/masif_site_contract/),
[`examples/scannet_ppi_contract/`](examples/scannet_ppi_contract/), and
[`examples/dmasif_site_contract/`](examples/dmasif_site_contract/).

## How it works — five organs

| Organ | Role |
|---|---|
| **Sandbox** | Disposable container; every expensive success is snapshotted so a later failure never re-pays the build. |
| **Commit-era pinner** | Reconstructs the dependency universe *as it was* on the repo's last commit, from the PyPI release timeline. |
| **Repair loop** | build → run → read traceback → patch → retry, bounded, isolated to the container. |
| **Capability locator** | Finds where "input → the famous output" happens and carves the minimal path to it. |
| **Contract emitter** | Module + CLI + pinned container + smoke test encoding your sanity check. |

## Runs on a laptop, executes anywhere

Lazarus runs on your machine; *where it executes* is pluggable via one flag. Local
containers for anything that runs under emulation — or a remote x86 host for methods
like MaSIF whose binaries (MSMS, TensorFlow) need native x86 that Apple-silicon
emulation can't provide:

```bash
lazarus resurrect ... --docker-host ssh://you@your-x86-box
```

The MaSIF resurrection above was **driven from a MacBook and executed on a native-x86
workstation** over exactly that flag.

Any Docker daemon reachable over SSH qualifies — a lab workstation, a **cloud VM**
(EC2/GCE), or a rented **GPU box** (Lambda, RunPod). The agent's tools issue
`docker exec`/`docker cp` against whatever daemon `DOCKER_HOST` points at, so the whole
resurrection orchestrates on the remote host with no host-specific code. The emitted
`predict.py` copies inputs/outputs with `docker cp` (not bind-mounts), so the *delivered*
component is host-agnostic too.

## Quickstart

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev,agent]"     # agent extra needs Python ≥ 3.10

# 1) Commit-era dependency pinning — no repo execution required
lazarus pin --date 2019-01-01 tensorflow numpy scipy biopython
#   tensorflow==1.12.0   (matches MaSIF's real Dockerfile, not its README)

# 2) Resurrect a capability in a sandbox (needs Docker + Claude auth)
lazarus resurrect \
  --image pablogainza/masif:latest --workdir /masif \
  --goal-file examples/masif_site_goal.txt --keep
```

**Auth:** Lazarus drives Claude via the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python).
Either log in the `claude` CLI (uses your subscription) or drop
`ANTHROPIC_API_KEY=...` in a gitignored `.env` at the repo root (uses API credit).

## Status

Working today: the pinner, the Docker sandbox (local + `ssh://` remote), the autonomous
repair loop, the capability locator, and the contract emitter — with **two** dead repos
(MaSIF-site and ScanNet) resurrected end-to-end, a head-to-head comparison on the PD-L1
interface, and 31 passing unit tests. Generalization: **proven**.

Next: run it on our own binder-triage targets, a residue-level output mode for MaSIF, and
a wider zoo of dead repos.

## License

MIT — see [LICENSE](LICENSE).
