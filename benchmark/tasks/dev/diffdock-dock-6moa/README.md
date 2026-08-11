# diffdock-dock-6moa — provenance

A `predict` task: blind-dock a small molecule into a receptor and land near the pose it
actually adopts in the crystal.

## Input

- `input/receptor.pdb` — **BRD2 BD2 bromodomain**, chain A, 109 residues, protein ATOM
  records only. Produced by the `dock_prep` brick from PDB **6MOA**.
- `input/jw4.smi` — the ligand as SMILES. JW4's canonical descriptor from the
  [RCSB chemical-component API](https://data.rcsb.org/rest/v1/core/chemcomp/JW4).

The pocket is *not* given. Finding it is part of the task.

## Ground truth

`labels/reference_ligand.pdb` — the crystal pose of JW4 as deposited in 6MOA, 30 heavy
atoms, extracted from the complex by `dock_prep`. Public in the PDB, but not recoverable
from the receptor-only input, which is what keeps it a fair target.

## Scoring

Heavy-atom **centroid distance** in Å, `≤ 2.0` to pass — the conventional docking-success
bar. Centroid rather than RMSD deliberately: DiffDock rebuilds the ligand from SMILES and
does not preserve atom order, so a same-order RMSD punishes a correct pose. On this exact
system the flagship pipeline measured **0.22 Å centroid against 5.30 Å same-order RMSD**.
Centroid distance is order-robust and grades every submission the same way.

DiffDock is generative, so repeat runs move by roughly 0.02 Å here — three orders of
magnitude inside the bar, so the task is stable despite the stochasticity.

## Why `dev`, not `test`

DiffDock is in the Lazarus registry with a pullable image, and 6MOA is the flagship
pipeline's hero system — the answer is published in this very repo
(`pipelines/sample_output_6MOA/`). Useless for ranking; ideal for developing the harness,
because the expected result is known to two decimal places.

Paired with `equibind-dock-6moa`: same target, same bar, different repo and era, so the
pair exercises the board comparing *methods* rather than implementations.
