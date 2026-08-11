# Compose & reproduce

## Compose — a pipeline from revived bricks

Because every revival speaks the same contract, revived tools compose regardless of domain,
language, or era. A pipeline is a small YAML; one command runs it, passing file artifacts between
steps on the host you choose.

Two pipelines, one question — *is this target a druggable small-molecule cleft, or a flat
protein-protein interface?* — reaching opposite, both-correct verdicts. **PD-L1** comes back a
biologic target. **BRD2** comes back a small-molecule one, cross-validated sub-Å against the drug
already sitting in its crystal structure.

### PD-L1 → a flat interface

[`examples/pipelines/binder_triage.yaml`](https://github.com/DoctorDean/lazarus/blob/main/examples/pipelines/binder_triage.yaml)
assembles three methods that were each individually unrunnable a week ago:

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

Run live on **PD-L1**, it concluded: **27 interface residues** clearly localized, but **0 druggable
pockets** among them → *"a flat protein-protein interface: an antibody / biologic target, not a
small-molecule one."* That's textbook immuno-oncology (PD-1/PD-L1 *is* an antibody target),
reproduced from dead code.

### BRD2 → a confirmed drug pocket

[`pipelines/target_dock_consensus.yaml`](https://github.com/DoctorDean/lazarus/blob/main/pipelines/target_dock_consensus.yaml)
asks the same question of a different target and takes it a step further — it doesn't just locate
the site, it docks a drug into it. Four tools spanning **2010→2023, C→Python, CPU→GPU,
geometry→learned→generative**, feeding one consensus adapter:

```
        ─▶ fpocket  (2010 C · geometry)       ─┐
complex ─▶ ScanNet  (learned · PPI-site)      ─┼─▶ consensus ─▶ CONFIRMED small-molecule site
        ─▶ DiffDock (2023 · generative · GPU) ─┤
        ─▶ EquiBind (generative · CPU)        ─┘
```

`dock_prep` splits the crystal complex into receptor and reference ligand; the JW4 SMILES feeds the
two dockers.

```bash
lazarus run pipelines/target_dock_consensus.yaml \
  --input complex=6moa.pdb --input ligand_smiles=jw4.smi \
  --registry examples --registry pipelines \
  --docker-host ssh://you@your-x86-gpu-box
```

Run live on **BRD2's BD2 bromodomain** (PDB 6MOA, 109 residues, chain A) — a validated BET oncology
target — the four methods reinforce rather than cancel. fpocket's top pocket scores **druggability
0.93** over 21 lining residues; ScanNet, asked the PPI question across those same residues, stays
**quiet (mean 0.26)** — the signature of a small-molecule cleft, not an interface. Both dockers land
*inside* that pocket: DiffDock's top pose sits **0.20 Å** (centroid) from the crystal ligand, 90% of
its contacts in the pocket; EquiBind independently lands at **0.84 Å centroid / 1.30 Å RMSD**, 100%
in-pocket (atom order preserved, so that RMSD means what it says); and the two generative dockers
agree with *each other* to **1.02 Å**. Decisively, both converge on **Asn429** (the conserved
acetyl-lysine anchor) and **Trp370** (the WPF-shelf tryptophan) — the real BET pharmacophore, not
merely *somewhere on the protein*. Verdict: *"CONFIRMED small-molecule site"* — the same question
PD-L1 answered, with the opposite result, this one cross-validated sub-Å against the drug already in
the crystal. One command, run on a remote A4500 GPU box (Bertha) via `--docker-host ssh`.

The whole run is committed — every output file, the exact command, and an honest note on what
reproduces exactly and what doesn't — at
[`pipelines/sample_output_6MOA/`](https://github.com/DoctorDean/lazarus/tree/main/pipelines/sample_output_6MOA).
fpocket, ScanNet and EquiBind are deterministic and repeat exactly; DiffDock is a *generative*
model, so its pose shifts slightly between runs (a second independent run gave 0.22 Å / 91% /
0.96 Å). The verdict, the pocket, and the Asn429 + Trp370 convergence are stable across both.

## Reproduce — the trust layer

A smoke test proves a method *runs*; a benchmark proves it's *the method*. A contract's `benchmark`
field emits a `REPRODUCE.md` certificate with a PASS/OFF verdict.

| Method | Paper | Lazarus | Verdict |
|---|:--:|:--:|:--:|
| **MaSIF-site** transient PPI benchmark | 0.85 | 0.82 | reproduced (±0.05) |
| **Basset** mean AUROC over 164 cell types | 0.895 | 0.8944 | reproduced |

Basset's reproduction is what *exposed* a silent bug: the naive run scored mean AUROC 0.675 because
half the genome's soft-masked (lowercase) bases fell through the one-hot encoder. Reproducing the
paper — not merely executing the code — is what caught it. Full story:
[the hard problems it solved](CHALLENGES.md).

## Give back

For the genuinely-abandoned repos, Lazarus prepares maintainer-ready PRs — the real fix plus a CI
smoke test so the method can't silently rot again:

- **MaSIF** — [PR #93](https://github.com/LPDI-EPFL/masif/pull/93): the rotted PDB download, fixed.
- **ScanNet** — [PR #16](https://github.com/jertubiana/ScanNet/pull/16): `library_folder=''` auto-detects the repo root.
