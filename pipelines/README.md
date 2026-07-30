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

> **Status:** built + structurally validated (bricks resolve, pipeline topo-sorts, fusion logic
> unit-checked on synthetic inputs). Two DiffDock integration points (relative `protein_path` in the
> CSV; nested `rank1.sdf` output) are flagged in the pipeline YAML and get resolved on the first
> GPU run.
