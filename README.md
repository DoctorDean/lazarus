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

## Proof — MaSIF, resurrected in one autonomous run

The anchor case is [**MaSIF**](https://github.com/LPDI-EPFL/masif) (LPDI-EPFL) — a
widely-cited molecular-surface-fingerprint method, ~5 years dormant, trapped behind
Python 3.6, TensorFlow 1.12, a from-source PyMesh build, and an external-binary chain
(MSMS, APBS, PDB2PQR, reduce). Lazarus resurrected its interaction-site predictor
**fully autonomously**:

| | |
|---|---|
| Repo state | ~763 ★ · 53 open issues · **~5 years dormant** |
| Run | **18 agent turns**, no human input |
| Sanity check | ROC-AUC of predicted interface vs. ground truth on `4ZQK_A` (PD-L1) |
| **Result** | **ROC-AUC = 0.9137** (threshold 0.80 · paper reports ≈ 0.85) |
| Verification | The **emitted package passes its own smoke test** standalone — no agent, pure Docker |
| Wall-clock | Working in **under half a day** |

📄 **The resurrection report** (a clinical case-file of the run) lives at
[`docs/resurrection_report.html`](docs/resurrection_report.html), and the actual package
Lazarus emitted is in [`examples/masif_site_contract/`](examples/masif_site_contract/).

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
repair loop, the capability locator, and the contract emitter — with MaSIF-site
resurrected end-to-end (ROC-AUC 0.9137) and 31 passing unit tests.

Next: prove it generalizes on a second dead repo, a residue-level output mode, and a
dMaSIF cross-check.

## License

MIT — see [LICENSE](LICENSE).
