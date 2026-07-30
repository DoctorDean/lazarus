#!/usr/bin/env python3
"""dock_prep — standardise a single complex PDB into inputs for the docking bricks.

complex PDB (protein + crystal-ligand HETATM) + ligand SMILES  ->
  receptor.pdb          protein ATOM records only (for fpocket / ScanNet / the consensus)
  reference_ligand.pdb  the largest non-solvent HETATM residue (crystal pose, for RMSD)
  diffdock.csv          DiffDock input row (complex_name,protein_path,ligand_description,protein_sequence)

EquiBind consumes the original complex PDB directly (it auto-splits the ligand), so no
separate EquiBind input is produced here.

Stdlib only — runs on a generic python image with no build.
"""
import os

# solvent / ions / common crystallisation additives to exclude when picking the ligand
SOLVENT = {"HOH", "WAT", "DOD", "NA", "CL", "K", "MG", "ZN", "CA", "MN", "FE", "CU",
           "SO4", "PO4", "GOL", "EDO", "PEG", "ACT", "DMS", "TRS", "IOD", "BR"}


def main():
    out = os.environ["OUTDIR"]
    os.makedirs(out, exist_ok=True)
    smiles = os.environ.get("ligand_smiles", "").strip()

    atoms, het = [], {}   # het: (resname, chain, resseq) -> [lines]
    for ln in open(os.environ["complex"]):
        if ln.startswith("ATOM"):
            atoms.append(ln)
        elif ln.startswith("HETATM"):
            rn = ln[17:20].strip()
            if rn in SOLVENT:
                continue
            het.setdefault((rn, ln[21], ln[22:26].strip()), []).append(ln)

    with open(os.path.join(out, "receptor.pdb"), "w") as f:
        f.writelines(atoms)
        f.write("END\n")

    ref = max(het, key=lambda k: len(het[k])) if het else None   # largest het group = ligand
    with open(os.path.join(out, "reference_ligand.pdb"), "w") as f:
        if ref:
            f.writelines(het[ref])
        f.write("END\n")

    # protein_path is RELATIVE — the receptor is co-located in the DiffDock step dir.
    # (Verify/adjust when the pipeline first runs on the GPU box; see the pipeline YAML.)
    with open(os.path.join(out, "diffdock.csv"), "w") as f:
        f.write("complex_name,protein_path,ligand_description,protein_sequence\n")
        f.write(f"target,receptor.pdb,{smiles},\n")

    print(f"receptor_atoms={len(atoms)} het_groups={len(het)} "
          f"reference_ligand={('/'.join(ref) if ref else 'none')} "
          f"smiles={'yes' if smiles else 'MISSING'}")


if __name__ == "__main__":
    main()
