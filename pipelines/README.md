# pipelines/

Multi-tool pipelines composed from registry bricks — *real science from resurrected code*
(Tier-1 flagship on the [roadmap](../docs/roadmap.md)). Because every revival speaks the same
contract, tools compose across domain, language, and era; a pipeline is a small YAML that
`lazarus run` executes, passing file artifacts between steps.

## `target_dock_consensus` — triangulate a druggable site
Four independently-resurrected tools, cross-validated against the crystal ligand:

```
fpocket  (geometry)   ─┐
ScanNet  (learned)    ─┼─▶ dock_site_consensus ─▶ do all four converge on one binding site?
DiffDock (generative) ─┤
EquiBind (generative) ─┘
```

The headline is **consensus**: not "the tools ran," but "orthogonal geometry, learned, and
generative signals *localise to the same pocket*" — a stronger, verifiable statement (RMSD to the
known ligand). Run on **6MOA** (DiffDock's hero system) it should conclude: both docked poses land
in the pocket fpocket flags druggable and ScanNet flags a site.

```bash
lazarus run pipelines/target_dock_consensus.yaml \
  --input complex=6moa.pdb --input ligand_smiles="<SMILES>" \
  --registry examples --registry pipelines \
  --docker-host ssh://you@your-gpu-box
```

**Bricks here:**
- `dock_prep` — split a complex PDB into a receptor, a reference ligand, and a DiffDock CSV.
- `dock_site_consensus` — the fusion: map each docked pose → contact residues, score overlap with
  the druggable pocket + the predicted site, and report pose-vs-crystal and pose-vs-pose RMSDs.

Both adapters are stdlib/numpy-only (generic `python:3.11-slim`, no build). `consensus.py` /
`prep.py` are the readable, locally-testable sources; the same code is embedded in each brick's
`lazarus.yaml` entrypoint so the contract is self-contained.

> **Status:** verified end-to-end on the A4500 GPU box (BRD2 / **6MOA**), twice. fpocket flags a
> druggable pocket (druggability **0.93**); DiffDock and EquiBind both dock JW4 into it (90–91% /
> 100% pocket overlap, **0.20–0.22 Å** / 0.84 Å from the crystal-ligand centroid; DiffDock↔EquiBind
> agree to ~1 Å); ScanNet stays quiet (mean p 0.26) — the signature of a small-molecule cleft, not a
> PPI interface. Both dockers converge on **Asn429** and **Trp370**, the real BET pharmacophore.
> Verdict: **CONFIRMED small-molecule site**, three independently-resurrected tools converging
> (fpocket geometry + DiffDock + EquiBind generative), cross-validated against the crystal ligand.
>
> The committed run — every output file, the exact command, and which numbers are deterministic
> vs. run-to-run (DiffDock is generative) — is in
> [`sample_output_6MOA/`](sample_output_6MOA/README.md).
