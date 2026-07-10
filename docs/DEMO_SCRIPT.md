# Lazarus — 3-minute demo video script

The companion to the [zero-setup Colab notebook](../notebooks/Lazarus_Democratizing_Dead_SOTA.ipynb).
This video shows the live thing: Lazarus reviving a famous, 2-years-stale model **from a bare URL**,
and docking a ligand back into its pocket.

> **Golden rule:** only run *live* what is fast and reliable — the `pip install`, the **Scout
> planning from a URL** (~40 s, pauses at a confirm prompt), and a **pre-warmed** result. The full
> revive (image pull + GPU + ESM + diffusion sampling) is **pre-recorded b-roll, fast-forwarded.**

---

## Pre-flight checklist

**Bertha (the A4500 GPU host)**
- [ ] Online and reachable: `tailscale status` shows `big-bertha` active; `ssh dean@100.80.108.2 true` returns instantly.
      ⚠️ Bertha has been idle-suspending and dropping off the tailnet — **disable sleep/suspend for the recording** (`sudo systemctl mask sleep.target suspend.target`), or keep a keep-alive running.
- [ ] DiffDock ready: `docker images | grep lazarus/diffdock` shows `:site-ready` (+ `:inference-ready`), and `rbgcsail/diffdock:latest` is present (pre-pulled — a fresh pull over the ssh tunnel times out).
- [ ] The 6MOA hero inputs are baked into `lazarus/diffdock:site-ready` (`/home/appuser/DiffDock/lazarus_bench/6moa/`).
- [ ] Compose bricks present: `lazarus/{masif,scannet,dmasif,fpocket,basset}` images (for the pipeline montage).

**Mac (the control plane — what's on screen)**
- [ ] `export DOCKER_HOST=ssh://dean@100.80.108.2`; venv active.
- [ ] `.env` has `ANTHROPIC_API_KEY`; `pip install lazarus-bio` already works (don't debug installs on camera).
- [ ] Terminal large (18–20 pt), dark theme, ~110 cols, scrollback cleared.
- [ ] Browser tabs: the PyPI page, the docs site, the Colab notebook, the two give-back PRs.

**Pre-recorded b-roll to capture beforehand**
- [ ] A full `lazarus resurrect https://github.com/gcorso/DiffDock --yes` run captured start→contract, to fast-forward in Beat 3.
- [ ] The **6MOA docked pose**: DiffDock's `rank1.sdf` overlaid on the crystal ligand (PyMOL/py3Dmol), RMSD 0.35 Å on screen — the hero image/animation.
- [ ] The `lazarus run binder_triage.yaml` pipeline output (or reuse `examples/pipelines/sample_output_4ZQK/`).

---

## The cut (target 3:00)

### 0:00–0:18 — The wall (hook)
**On screen:** the DiffDock GitHub page (famous, ICLR 2023), last commit ~2 years ago; a terminal
`python -m inference …` erroring on a dead dependency.
**VO:** "This is one of the best molecular-docking models in the world. Two years on, it doesn't
run. Most published methods don't, within a few years. Lazarus brings them back."

### 0:18–0:38 — It's one pip away
**On screen — live:** `pip install lazarus-bio` → done in seconds; flash the PyPI + docs badges.
**VO:** "Lazarus is an agent that revives dead research code — and anyone can install it."

### 0:38–1:30 — THE LIVE MOMENT: revive from a URL
**On screen — type it live:**
```bash
lazarus resurrect https://github.com/gcorso/DiffDock
```
The **Scout reads the repo + paper and prints its plan live** (~40 s): the capability, the base
image, and the sanity check — *top-1 pose within 2 Å of the crystal ligand*. It **pauses at a
confirm prompt** (natural hold). → cut to **fast-forwarded b-roll** of the repair loop pulling the
CUDA/PyG/ESM stack and running diffusion sampling on the GPU → lands on **contract emitted**.
**VO:** "You hand it nothing but a link. It reads the repo and the paper itself, decides what
'working' even means, and fights the whole dead stack on a GPU — unattended."

### 1:30–2:05 — The payoff, and the honesty
**On screen:** the 6MOA docked pose — DiffDock's top-1 (pre-rendered) snapping onto the crystal
ligand, **RMSD 0.35 Å**.
**VO:** "The shipped example was actually a *hard* case — so instead of faking a pass, it tested
DiffDock's own benchmark, reproduced its ~40 % top-1 accuracy, and nailed this one at a third of an
ångström. It won't ship a green checkmark it didn't earn."

### 2:05–2:35 — Breadth + compose
**On screen:** quick montage of the **six** bricks, then the one-liner
`lazarus run examples/pipelines/binder_triage.yaml …` → the PD-L1 result.
**VO:** "It's done this six times — TensorFlow, CUDA, 15-year-old C, Lua Torch7, diffusion models.
And because every revival emits the same contract, they compose: on PD-L1 the pipeline calls it —
a flat interface, an antibody target. Reproduced from dead code."

### 2:35–3:00 — Close
**On screen:** the give-back PRs (#93, #16); then `pip install lazarus-bio`, the docs site, "Open in
Colab."
**VO:** "Every fix goes back upstream as a pull request. Install it, open the notebook, point it at
a dead repo. Dead state-of-the-art, one command away. That's Lazarus."
**End card:** `pip install lazarus-bio` · `github.com/DoctorDean/lazarus`

---

## If something breaks on camera (fallbacks)
- **Bertha offline / drops mid-shot:** skip the live revive; the Scout plan (0:38) still runs
  (it's host-side, no Bertha) — show that + the pre-recorded revive b-roll + the pre-rendered 6MOA
  pose. Nothing here needs Bertha live.
- **`lazarus resurrect` is slow to plan:** the Scout is deterministic-ish and ~40 s; if it stalls,
  cut to the pre-recorded plan.
- **Any live cell stalls:** cut to the Colab notebook (needs no compute) and the pre-rendered pose.

## Sticky-note commands
```bash
export DOCKER_HOST=ssh://dean@100.80.108.2
pip install lazarus-bio
lazarus resurrect https://github.com/gcorso/DiffDock        # live: Scout plan, then Ctrl-C at the prompt
# pre-warm the pieces the day of:
ssh dean@100.80.108.2 'docker pull rbgcsail/diffdock:latest'  # avoid an on-camera pull
lazarus run examples/pipelines/binder_triage.yaml --input structure=4ZQK.pdb \
  --registry examples --registry components --docker-host ssh://dean@100.80.108.2
```
