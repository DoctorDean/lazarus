# equibind-dock-6moa — provenance

A `predict` task: blind-dock a small molecule into a receptor and land near its crystal
pose. Deliberately the **same target, input and bar** as
[`diffdock-dock-6moa`](../diffdock-dock-6moa/README.md) — two repos, two eras, one
criterion, so the pair shows the board comparing methods rather than implementations.

## Input and ground truth

Identical to the DiffDock task: `input/receptor.pdb` (BRD2 BD2 bromodomain, chain A, from
PDB **6MOA**), `input/jw4.smi` (the ligand as SMILES from the RCSB chemical-component API),
and `labels/reference_ligand.pdb` (the deposited crystal pose of JW4, 30 heavy atoms). The
pocket is not supplied. See the DiffDock task's README for the full derivation.

## Scoring

Heavy-atom **centroid distance** in Å, `≤ 2.0` to pass.

EquiBind re-poses the ligand it is given and *does* preserve atom order, so a same-order
RMSD would be meaningful here — the flagship measured **0.84 Å centroid / 1.30 Å RMSD**.
The task still scores centroid distance, because both docking tasks must be graded by the
same rule for the comparison to mean anything. Using each tool's most flattering metric
would be exactly the kind of self-chosen criterion this layer exists to eliminate.

Unlike DiffDock, EquiBind is a one-shot regression, so this task is deterministic.

## Why `dev`, not `test`

EquiBind is in the Lazarus registry with a pullable image, and this result is published in
`pipelines/sample_output_6MOA/`. Known answer, so it develops the harness rather than
ranking anyone.
