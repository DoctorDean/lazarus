# dmasif-ppi-4zqk — provenance

A `predict` task: score every residue of one protein chain for whether it sits at a
protein-protein interface. **Same input, labels and bar as
[`scannet-ppi-4zqk`](../scannet-ppi-4zqk/README.md)** — one question, two repos.

## Input and ground truth

Identical to the ScanNet task, and copied from it so each task stays self-contained:

- `input/4ZQK_A.pdb` — chain A of PDB **4ZQK** (PD-L1 / PD-1), protein ATOM records only,
  115 residues.
- `labels/interface_5A.csv` — `label=1` for the **22 of 115** residues with any heavy atom
  within 5.0 Å of any chain-B heavy atom, rebuilt from the deposited structure. The partner
  chain is not shipped; recovering the interface is the task.

See the ScanNet task's README for the full derivation.

## Why a second task on the same target

The two methods take genuinely different routes to the same answer — ScanNet reasons over a
residue graph, dMaSIF over a molecular surface — and dMaSIF needs a GPU, so it exercises a
harder execution path than ScanNet does. Holding the input, labels and threshold fixed
across both is what lets the board attribute a difference to the *method* rather than to a
task that happened to be easier.

Recorded revival results on this exact input: **dMaSIF 0.8390**, ScanNet 0.9233. Grading
the committed dMaSIF residue scores through this task's evaluator returns 0.8390, matching.

## Licensing note for submitters

dMaSIF is CC-BY-NC-ND. That's why the Lazarus registry ships it rebuild-locally instead of
as a pullable image, and it's why a submission may not redistribute a built image of it.
The task points at the source; obtaining and building it is the submission's problem —
which is itself a fair part of what "revive this" means.

## Why `dev`, not `test`

dMaSIF is in the registry with a published contract and a known result on this input.
