# scannet-ppi-4zqk — provenance

A `predict` task: given one protein chain, score every residue for whether it sits at a
protein-protein interface. Graded by AUROC against labels the submission never sees.

## Input

`input/4ZQK_A.pdb` — chain A of **PDB 4ZQK** (PD-L1 in complex with PD-1), protein ATOM
records only, 115 residues. Copied from `examples/pipelines/sample_output_4ZQK/4ZQK.pdb`.

## Labels

`labels/interface_5A.csv` — one row per chain-A residue, `label=1` if **any heavy atom is
within 5.0 Å of any chain-B heavy atom**, else 0. **22 of 115 residues are positive.**

Built from the full deposited structure, which contains the partner chain the input
deliberately omits:

```bash
curl -O https://files.rcsb.org/download/4ZQK.pdb
# for each chain-A residue: min heavy-atom distance to any chain-B heavy atom <= 5.0 A
```

Hydrogens excluded. The partner chain is *not* shipped with the task — recovering the
interface is the point, so handing over chain B would give the answer away.

## Why this task is in `dev`, not `test`

ScanNet is one of the 25 tools in the Lazarus registry: its working contract, base image
and sanity metric are all published, and this exact input (4ZQK chain A) is the sanity
check its revival used. The answer is a `docker pull` away. That makes it worthless for
ranking and ideal for developing the harness — a task whose expected outcome we know
exactly.

The 5 Å interface definition and this input are also what the original revival was scored
on, which is why the recorded ScanNet result (**AUROC 0.9233**) is directly comparable to
what this task measures. The threshold is set at 0.70 — clearing it means the interface
was genuinely localised, not merely that something ran.
