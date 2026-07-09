# Lazarus — 3-minute demo video script

The **live-compute** companion to the [zero-setup Colab notebook](../notebooks/Lazarus_Democratizing_Dead_SOTA.ipynb).
The notebook teaches Lazarus with no Docker and no accounts; **this video shows the
real thing running** — the autonomous revival, and a pipeline of four just-revived
tools executing on a GPU box in one command.

> **Golden rule for a 3-minute cut:** don't run the slow parts live. The full
> resurrections take 18–51 agent-turns (minutes each). Pre-record that b-roll and
> **fast-forward it**; run *live* only the things that finish in seconds (the
> pinner, `lazarus run` against a **pre-warmed** box). Everything below is timed
> for a pre-warmed setup.

---

## Pre-flight checklist (do this before you hit record)

**Bertha (the A4500 x86 GPU box) — the compute host**
- [ ] Box online and reachable: `tailscale status` shows it; `ssh dean@100.80.108.2 true` returns instantly.
- [ ] Docker up on the box; the four images present:
      `docker images | grep -E 'lazarus/(masif|scannet|dmasif|fpocket)'`
      → `lazarus/masif:site-ready`, `lazarus/scannet:ppi-noMSA-proven`, `lazarus/dmasif:site-ready`, `lazarus/fpocket:working`.
- [ ] **Warm the images** so nothing pulls/builds on camera: run `binder_triage.yaml` once end-to-end *before* recording (also confirms the demo works today).

**Mac (the control plane — what's on screen)**
- [ ] `export DOCKER_HOST=ssh://dean@100.80.108.2` in the demo shell (Lazarus drives Bertha over this).
- [ ] `.env` has `ANTHROPIC_API_KEY` (billed to hackathon credit); venv active: `source .venv/bin/activate`.
- [ ] `4ZQK.pdb` present in the repo root (`cp pipeline-output/fpocket/4ZQK.pdb .`).
- [ ] Terminal font **large** (18–20pt), dark theme, window ~110 cols. Clear scrollback.
- [ ] Browser tabs pre-opened: the Colab notebook, the repo, `docs/CHALLENGES.md`, the two PR pages.

**Pre-recorded b-roll to capture beforehand**
- [ ] A real `lazarus resurrect` run (fpocket or dMaSIF is most dramatic) captured start→contract, to fast-forward in Beat 1.
- [ ] The Colab notebook's 3D view already rendered (so Beat 4 doesn't wait on a cell).

---

## The cut (target 3:00)

### 0:00–0:18 — The wall (hook)
**On screen:** a GitHub repo, last commit ~5 years ago, `pip install` erroring in red.
**VO:** "Most published biology methods stop running within a few years. The code
is open and cited — and completely dead. Lazarus is an agent that brings them back,
composes them, and mails the fix upstream. Here's four of them, resurrected."

### 0:18–1:05 — REVIVE (pre-recorded, fast-forwarded)
**On screen:** the `lazarus resurrect` b-roll, sped up. Let a few real tracebacks
flash by, then the emitted contract + `SMOKE PASS`.
**VO:** "You point it at a dead repo and give it a goal — a task plus a sanity
check. It runs a build-run-read-the-traceback-and-patch loop in a sandbox. On
fpocket, a 2010 C program, it worked around a SourceForge download wall, fixed a
modern-linker break, and patched a **fifteen-year-old undefined-behaviour bug** that
was silently producing empty output. Zero human edits. Out comes a callable
contract with a passing smoke test."
**Lower-third:** *4 repos · ~120 autonomous turns · TensorFlow / CUDA / 2010 C*

### 1:05–2:05 — COMPOSE (LIVE, the centerpiece)
**On screen — type and run:**
```bash
lazarus run examples/pipelines/binder_triage.yaml \
    --input structure=4ZQK.pdb \
    --registry examples --registry components \
    --docker-host ssh://dean@100.80.108.2
```
Let the step log scroll: `scannet ▸ dmasif (GPU) ▸ fpocket ▸ consensus`. Then `cat`
the summary.
**VO:** "Because every revival emits the *same* contract, they compose. This one
command runs three of them — ScanNet, dMaSIF on the GPU, and fpocket — plus a
consensus step, on my x86 box over a single flag. On PD-L1: twenty-seven interface
residues, but zero druggable pockets. Its conclusion —" *(point at the summary)* "—
a flat protein-protein interface: an antibody target, not a small-molecule one.
That's textbook immuno-oncology, reproduced from code that was dead a week ago."

### 2:05–2:35 — REPRODUCE + GIVE BACK
**On screen:** `cat examples/masif_site_contract/REPRODUCE.md` (0.82 vs paper 0.85 →
REPRODUCED); then flip to the two open PR tabs.
**VO:** "A smoke test proves it runs; this proves it's *the method* — MaSIF-site
reproduces its published benchmark within tolerance. And every fix Lazarus finds
becomes a maintainer-ready pull request with CI, so the method can't silently rot
again."

### 2:35–3:00 — Democratize (the Colab close)
**On screen:** the Colab notebook — scroll to the rendered 3D PD-L1 view (interface
in red).
**VO:** "And you don't need any of my setup to see it. This notebook opens in a
browser — no Docker, no GPU — runs the dependency pinner live, and renders the whole
result in 3D. Dead state-of-the-art, one click away. That's Lazarus."
**End card:** `github.com/DoctorDean/lazarus` + the "Open in Colab" badge.

---

## If something breaks on camera (fallbacks)
- **Bertha offline / slow:** skip the live `lazarus run`; show `cat
  examples/pipelines/sample_output_4ZQK/summary.txt` and the pre-recorded pipeline
  b-roll instead. The conclusion is identical.
- **`DOCKER_HOST` SSH hiccup:** `ssh dean@100.80.108.2 docker ps` to prove
  reachability, then retry; or fall back to the sample output as above.
- **Any live cell stalls:** cut to the pre-rendered Colab 3D view — it needs no
  compute and always works.

## One-liners to have on a sticky note
```bash
export DOCKER_HOST=ssh://dean@100.80.108.2
source .venv/bin/activate
cp pipeline-output/fpocket/4ZQK.pdb .
# warm-up (run before recording):
lazarus run examples/pipelines/binder_triage.yaml --input structure=4ZQK.pdb \
  --registry examples --registry components --docker-host ssh://dean@100.80.108.2
```
