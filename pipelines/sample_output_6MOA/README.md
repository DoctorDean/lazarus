# sample_output_6MOA — the flagship result, as it came out of the pipeline

Committed output of [`target_dock_consensus`](../target_dock_consensus.yaml) run on **BRD2's
BD2 bromodomain** (PDB **6MOA**, chain A, 109 residues) — a validated BET oncology target — with
its crystal ligand **JW4**. Four independently-resurrected tools spanning 2010→2023, C→Python,
CPU→GPU, geometry→learned→generative, feeding one consensus adapter.

Every file here is a real artifact of the run below; nothing is hand-written.

## The command

```bash
curl -o 6moa.pdb https://files.rcsb.org/download/6MOA.pdb
printf 'Cc1onc(C)c1c2cc3[nH]c(nc3c(c2)c4c(C)ccc5ncccc45)C6CC6\n' > jw4.smi

lazarus run pipelines/target_dock_consensus.yaml \
  --input complex=6moa.pdb --input ligand_smiles=jw4.smi \
  --registry examples --registry pipelines \
  --docker-host ssh://you@your-gpu-box
```

The SMILES is JW4's canonical descriptor from the [RCSB chemical-component
API](https://data.rcsb.org/rest/v1/core/chemcomp/JW4)
(4-(2-cyclopropyl-7-(6-methylquinolin-5-yl)-1H-benzo[d]imidazol-5-yl)-3,5-dimethylisoxazole).
Run on an NVIDIA RTX A4500 box, 2026-08-11.

## The verdict

> **CONFIRMED small-molecule site.** fpocket flags a druggable pocket (druggability 0.93);
> diffdock + equibind dock the ligand into it (0.22 Å from the crystal ligand). ScanNet
> (a PPI-interface predictor) stays quiet — the signature of a small-molecule cleft, not a
> protein-protein interface.

| Tool | Era / kind | Result |
|---|---|---|
| fpocket | 2010 C · geometry | top pocket druggability **0.93**, 21 lining residues |
| ScanNet | learned · PPI-site | mean p **0.26** over those residues — quiet |
| DiffDock | 2023 · generative · GPU | 11 contacts, **91%** in-pocket, **0.22 Å** from crystal centroid |
| EquiBind | generative · CPU | 8 contacts, **100%** in-pocket, **0.84 Å** centroid / **1.30 Å** RMSD |

The two dockers agree with each other to **0.96 Å** (centroid), and six residues are contacted by
*both* — including **Asn429** (the conserved acetyl-lysine anchor) and **Trp370** (the WPF-shelf
tryptophan). That's the real BET pharmacophore, not merely *somewhere on the protein*.

## Files

| File | From | What it is |
|---|---|---|
| `summary.txt` | `consensus` | the triangulation verdict (pipeline output) |
| `triage.csv` | `consensus` | per-residue: ScanNet p, in-top-pocket, contacted by each docker |
| `pockets.json` | `fpocket` | pockets + druggability + lining residues |
| `scannet_predictions.csv` | `scannet` | per-residue binding-site probability |
| `diffdock_rank1.sdf` | `diffdock` | top-ranked docked pose |
| `equibind_docked_ligand.sdf` | `equibind` | docked pose |
| `reference_ligand.pdb` | `prep` | crystal JW4 (30 heavy atoms), the RMSD reference |
| `receptor.pdb` | `prep` | protein-only ATOM records, what the other three bricks saw |
| `diffdock.csv`, `jw4.smi` | `prep` / input | the exact docking input row and SMILES |

## What reproduces exactly, and what doesn't

Worth stating plainly, since this is a reproducibility project:

- **fpocket, ScanNet, EquiBind are deterministic.** Re-running reproduces them exactly —
  druggability 0.93, mean p 0.26, and EquiBind's 0.84 Å / 1.30 Å / 100% land on the same numbers.
- **DiffDock is a generative (diffusion) model, so its pose moves slightly run to run.** Two
  independent runs of this pipeline on the same box gave **0.20 Å / 90% / 1.02 Å** and
  **0.22 Å / 91% / 0.96 Å** (centroid-to-crystal / pocket overlap / agreement with EquiBind).
  The verdict, the pocket, and the Asn429 + Trp370 convergence are stable; the second decimal
  of the centroid distance is not. The numbers in this directory are the second run.
- **`rmsd_to_ref` carries an atom-order caveat.** The consensus adapter computes a straight
  same-order heavy-atom RMSD. EquiBind re-poses the input ligand and preserves atom order, so its
  1.30 Å means what it says; DiffDock rebuilds the molecule from SMILES and does not, so its
  same-order RMSD (5.30 Å here) is not comparable — which is exactly why the headline geometry is
  centroid distance and contact-residue overlap, both order-robust. A symmetry-aware RMSD (rdkit)
  is the refinement.
