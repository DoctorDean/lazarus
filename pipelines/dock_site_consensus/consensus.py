#!/usr/bin/env python3
"""dock_site_consensus — the fusion core of the `target_dock_consensus` pipeline.

Triangulate a small-molecule binding site from four independently-resurrected tools:

  fpocket   (geometry)   -> druggable pocket + lining residues
  ScanNet   (learned)    -> per-residue functional-site probability
  DiffDock  (generative) -> a docked ligand pose
  EquiBind  (generative) -> a docked ligand pose

and report whether the two docked poses land in the pocket fpocket flags druggable and
ScanNet flags a site — i.e. whether all four converge on the same place.

Inputs are file paths passed as environment variables (the Lazarus compose runner sets
them from upstream step artifacts); outputs are written to $OUTDIR.

Dependency-light on purpose (stdlib + numpy) so it runs on a generic `python:3.11-slim`
image with no custom build. Geometry (contact residues, centroids) is order-robust and
carries the headline; straight heavy-atom RMSD is reported as a secondary number with an
explicit atom-order caveat.
"""
import os, csv, json, sys
import numpy as np

CONTACT_A = 4.0      # ligand-atom -> residue-atom distance (Å) that counts as contact
SITE_P = 0.5         # ScanNet probability that counts as a predicted site residue
DRUG = 0.5           # fpocket druggability that counts as "druggable"


# ---- parsers (stdlib only) -------------------------------------------------
def parse_pdb_residues(path, chain="A"):
    """resid -> (resname, Nx3 heavy-atom coords) for one chain (ATOM records)."""
    res = {}
    for ln in open(path):
        if not ln.startswith("ATOM"):
            continue
        if chain and ln[21].strip() and ln[21] != chain:
            continue
        elem = ln[76:78].strip() or ln[12:16].strip()[0]
        if elem == "H":
            continue
        rid = int(ln[22:26])
        xyz = (float(ln[30:38]), float(ln[38:46]), float(ln[46:54]))
        rn, coords = res.get(rid, (ln[17:20].strip(), []))
        coords.append(xyz)
        res[rid] = (rn, coords)
    return {r: (n, np.array(c, float)) for r, (n, c) in res.items()}


def parse_sdf_heavy_atoms(path):
    """Heavy-atom coords (Nx3) of the FIRST molecule in a V2000 SDF."""
    lines = open(path).read().split("$$$$")[0].splitlines()
    if len(lines) < 4:
        return np.empty((0, 3))
    natoms = int(lines[3][0:3])
    out = []
    for ln in lines[4:4 + natoms]:
        elem = ln[31:34].strip()
        if elem == "H":
            continue
        out.append((float(ln[0:10]), float(ln[10:20]), float(ln[20:30])))
    return np.array(out, float) if out else np.empty((0, 3))


def parse_ligand_any(path):
    """Heavy-atom coords from an SDF or a PDB (HETATM) reference ligand."""
    if path.lower().endswith((".sdf", ".mol")):
        return parse_sdf_heavy_atoms(path)
    out = []
    for ln in open(path):
        if ln.startswith("HETATM"):
            elem = ln[76:78].strip() or ln[12:16].strip()[0]
            if elem == "H":
                continue
            out.append((float(ln[30:38]), float(ln[38:46]), float(ln[46:54])))
    return np.array(out, float) if out else np.empty((0, 3))


# ---- geometry --------------------------------------------------------------
def contact_residues(lig_xyz, residues):
    """resids with any heavy atom within CONTACT_A of any ligand heavy atom."""
    hits = set()
    if len(lig_xyz) == 0:
        return hits
    for rid, (_, coords) in residues.items():
        if len(coords) and np.min(np.linalg.norm(
                coords[:, None, :] - lig_xyz[None, :, :], axis=-1)) <= CONTACT_A:
            hits.add(rid)
    return hits


def centroid_dist(a, b):
    if len(a) == 0 or len(b) == 0:
        return None
    return float(np.linalg.norm(a.mean(0) - b.mean(0)))


def rmsd_same_order(a, b):
    """Heavy-atom RMSD assuming a consistent atom order (both tools re-pose the SAME
    input ligand). Approximate — a symmetry/order-robust RMSD (rdkit) is the refinement."""
    if len(a) == 0 or len(b) == 0 or len(a) != len(b):
        return None
    return float(np.sqrt(((a - b) ** 2).sum(1).mean()))


# ---- fpocket / ScanNet -----------------------------------------------------
def _g(d, *keys, default=None):
    for k in keys:
        if k in d:
            return d[k]
    return default


def load_pockets(path):
    """-> list of {rank, druggability, residues:set[int]}, best-druggability first."""
    data = json.load(open(path))
    if isinstance(data, dict):
        data = _g(data, "pockets", default=[]) or []
    out = []
    for i, p in enumerate(data):
        resids = set()
        for r in _g(p, "lining_residues", "residues", "resids", default=[]) or []:
            try:
                resids.add(int(r))
            except (ValueError, TypeError):
                pass
        out.append({"rank": _g(p, "rank", "pocket", default=i + 1),
                    "drug": float(_g(p, "druggability", "drug_score",
                                     "druggability_score", default=0) or 0),
                    "residues": resids})
    out.sort(key=lambda x: -x["drug"])
    return out


def load_scannet(path, chain="A"):
    """resid -> binding-site probability, one chain."""
    sn = {}
    for row in csv.DictReader(open(path)):
        if row.get("Chain", chain).strip() not in (chain, ""):
            continue
        try:
            sn[int(row["Residue Index"])] = float(row["Binding site probability"])
        except (KeyError, ValueError, TypeError):
            pass
    return sn


# ---- main ------------------------------------------------------------------
def main():
    out = os.environ["OUTDIR"]
    os.makedirs(out, exist_ok=True)
    residues = parse_pdb_residues(os.environ["receptor"])
    pockets = load_pockets(os.environ["pockets"])
    scannet = load_scannet(os.environ["scannet"])
    top = pockets[0] if pockets else {"drug": 0.0, "residues": set(), "rank": None}

    poses = {}
    for tool, env in (("diffdock", "diffdock_pose"), ("equibind", "equibind_pose")):
        if os.environ.get(env) and os.path.exists(os.environ[env]):
            poses[tool] = parse_sdf_heavy_atoms(os.environ[env])
    ref = (parse_ligand_any(os.environ["reference_ligand"])
           if os.environ.get("reference_ligand") and os.path.exists(os.environ["reference_ligand"])
           else np.empty((0, 3)))

    # per-pose analysis
    analysis = {}
    for tool, xyz in poses.items():
        contacts = contact_residues(xyz, residues)
        in_pocket = contacts & top["residues"]
        site_contacts = {r for r in contacts if scannet.get(r, 0.0) >= SITE_P}
        analysis[tool] = {
            "n_contacts": len(contacts),
            "contacts": contacts,
            "pocket_overlap": len(in_pocket) / len(contacts) if contacts else 0.0,
            "site_overlap": len(site_contacts) / len(contacts) if contacts else 0.0,
            "mean_scannet": float(np.mean([scannet.get(r, 0.0) for r in contacts])) if contacts else 0.0,
            "rmsd_to_ref": rmsd_same_order(xyz, ref),
            "centroid_to_ref": centroid_dist(xyz, ref),
        }

    # pose agreement (order-robust centroid + best-effort RMSD)
    agree_centroid = agree_rmsd = None
    if "diffdock" in poses and "equibind" in poses:
        agree_centroid = centroid_dist(poses["diffdock"], poses["equibind"])
        agree_rmsd = rmsd_same_order(poses["diffdock"], poses["equibind"])

    # per-residue triage table
    all_ids = sorted(residues)
    with open(os.path.join(out, "triage.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["resid", "resname", "scannet_prob", "in_top_pocket",
                    "contacted_by_diffdock", "contacted_by_equibind"])
        for rid in all_ids:
            w.writerow([rid, residues[rid][0], round(scannet.get(rid, 0.0), 3),
                        int(rid in top["residues"]),
                        int(rid in analysis.get("diffdock", {}).get("contacts", set())),
                        int(rid in analysis.get("equibind", {}).get("contacts", set()))])

    # verdict — accurate to what actually ran; distinguishes a small-molecule pocket
    # (fpocket druggable, ScanNet quiet) from a PPI interface (ScanNet lit, no pocket).
    druggable = top["drug"] >= DRUG
    docked = [t for t in ("diffdock", "equibind") if t in analysis]
    in_pocket = [t for t in docked if analysis[t]["pocket_overlap"] >= 0.5]
    pocket_scannet = [scannet.get(r, 0.0) for r in top["residues"]]
    scannet_at_pocket = float(np.mean(pocket_scannet)) if pocket_scannet else 0.0
    is_ppi = scannet_at_pocket >= SITE_P
    with open(os.path.join(out, "summary.txt"), "w") as f:
        p = f.write
        p("Druggable-site consensus\n========================\n")
        p(f"receptor residues: {len(residues)} | docking tools with a pose: "
          f"{', '.join(docked) if docked else 'none'}\n")
        p(f"fpocket top pocket: rank {top['rank']}, druggability {top['drug']:.2f} "
          f"({'druggable' if druggable else 'not druggable'}), {len(top['residues'])} lining residues\n")
        p(f"ScanNet over that pocket: mean p={scannet_at_pocket:.2f} "
          f"({'a predicted interaction site' if is_ppi else 'quiet — not a PPI interface'})\n\n")
        for tool in ("diffdock", "equibind"):
            a = analysis.get(tool)
            if not a:
                p(f"{tool}: no pose (skipped / blocked)\n"); continue
            p(f"{tool} pose: {a['n_contacts']} contact residues, "
              f"{a['pocket_overlap']*100:.0f}% in the druggable pocket")
            if a["centroid_to_ref"] is not None:
                p(f"; vs crystal ligand centroid {a['centroid_to_ref']:.2f} Å"
                  + (f", RMSD {a['rmsd_to_ref']:.2f} Å (same-order)" if a["rmsd_to_ref"] is not None else ""))
            p("\n")
        if agree_centroid is not None:
            p(f"DiffDock vs EquiBind agreement: centroid {agree_centroid:.2f} Å"
              + (f", RMSD {agree_rmsd:.2f} Å\n" if agree_rmsd is not None else "\n"))
        p("\n=> ")
        conv = ["fpocket"] + in_pocket + (["ScanNet"] if is_ppi else [])
        if druggable and in_pocket:
            best = min((analysis[t]["centroid_to_ref"] for t in in_pocket
                        if analysis[t]["centroid_to_ref"] is not None), default=None)
            p(f"CONFIRMED small-molecule site. fpocket flags a druggable pocket "
              f"(druggability {top['drug']:.2f}); {' + '.join(in_pocket)} "
              f"dock{'s' if len(in_pocket) == 1 else ''} the ligand into it"
              + (f" ({best:.2f} Å from the crystal ligand)" if best is not None else "") + ".\n   "
              + ("ScanNet also flags it a protein-interaction site (a dual-function surface).\n"
                 if is_ppi else
                 "ScanNet (a PPI-interface predictor) stays quiet — the signature of a small-molecule\n"
                 "   cleft, not a protein-protein interface.\n")
              + f"   Independently-resurrected tools converging here: {' + '.join(conv)}.\n")
        elif not druggable and is_ppi:
            p("PPI / biologic target. ScanNet flags a functional interface but fpocket finds NO\n"
              "   druggable pocket there — a flat protein-protein interface (an antibody target,\n"
              "   not a small-molecule one).\n")
        else:
            p("Inconclusive — the docked pose(s) do not concentrate in the top druggable pocket;\n"
              "   inspect triage.csv.\n")

    # machine-readable line (for the pipeline's smoke/verify)
    dd = analysis.get("diffdock", {}); eb = analysis.get("equibind", {})
    print(f"pocket_druggability={top['drug']:.3f} "
          f"diffdock_pocket_overlap={dd.get('pocket_overlap', 0):.3f} "
          f"equibind_pocket_overlap={eb.get('pocket_overlap', 0):.3f} "
          f"pose_agreement_centroid_A={agree_centroid if agree_centroid is not None else 'NA'} "
          f"diffdock_centroid_to_ref_A={dd.get('centroid_to_ref', 'NA')}")


if __name__ == "__main__":
    main()
