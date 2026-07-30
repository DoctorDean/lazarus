"""Three-way head-to-head: MaSIF-site vs ScanNet vs dMaSIF on PD-L1 (4ZQK chain A).

All three methods are scored against the SAME ground truth at residue level:
chain-A residues with any heavy atom within 5.0 A of the partner chain (PD-1).

Usage:
    python analysis/compare_three_way.py <artifacts_dir>

<artifacts_dir> must contain (extracted with `docker cp` from the resurrected snapshots):
    4ZQK.pdb
    masif/pred_4ZQK_A.npy  masif/p1_X.npy p1_Y.npy p1_Z.npy  masif/p1_iface_labels.npy
    scannet/predictions_4ZQK_A.csv
    dmasif/4ZQK_A_residue_scores.npy  dmasif/4ZQK_A_residue_ids.npy

Requires: numpy, scipy, scikit-learn, biopython.
"""
import csv
import itertools
import os
import sys

import numpy as np
from Bio.PDB import NeighborSearch, PDBParser
from Bio.PDB.Polypeptide import is_aa
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

S = sys.argv[1] if len(sys.argv) > 1 else "artifacts"
CHAIN, CUTOFF = "A", 5.0

# ------------------------------------------------------------------ ground truth
model = PDBParser(QUIET=True).get_structure("x", os.path.join(S, "4ZQK.pdb"))[0]
A = model[CHAIN]
partner = [a for c in model if c.id != CHAIN for a in c.get_atoms() if a.element != "H"]
ns = NeighborSearch(partner)
labels, a_atoms, a_resid = {}, [], []
for res in A:
    if not is_aa(res, standard=True):
        continue
    rid, iface = res.id[1], 0
    for atom in res:
        if atom.element == "H":
            continue
        a_atoms.append(atom.coord)
        a_resid.append(rid)
        if ns.search(atom.coord, CUTOFF):
            iface = 1
    labels[rid] = iface
tree = cKDTree(np.array(a_atoms))
print(f"chain {CHAIN}: {len(labels)} residues | interface (<{CUTOFF}A): {sum(labels.values())}")

# ------------------------------------------------------------------ ScanNet (per-residue)
scannet = {}
with open(os.path.join(S, "scannet", "predictions_4ZQK_A.csv")) as fh:
    for row in csv.DictReader(fh):
        if row["Chain"].strip() == CHAIN:
            scannet[int(row["Residue Index"])] = float(row["Binding site probability"])

# ------------------------------------------------------------------ dMaSIF (per-residue, native)
d_ids = np.load(os.path.join(S, "dmasif", "4ZQK_A_residue_ids.npy"))
d_sc = np.load(os.path.join(S, "dmasif", "4ZQK_A_residue_scores.npy"))
dmasif = {int(r): float(s) for r, s in zip(d_ids, d_sc)}

# ------------------------------------------------------------------ MaSIF (vertex -> residue)
scores = np.load(os.path.join(S, "masif", "pred_4ZQK_A.npy")).reshape(-1)
verts = np.stack([np.load(os.path.join(S, "masif", f"p1_{c}.npy")) for c in "XYZ"], axis=1)
_, nn = tree.query(verts)
vert_res = np.array(a_resid)[nn]
masif = {}
for rid, sc in zip(vert_res, scores):
    masif.setdefault(int(rid), []).append(float(sc))
masif = {r: max(v) for r, v in masif.items()}

methods = {"ScanNet": scannet, "dMaSIF": dmasif, "MaSIF-site": masif}

# ------------------------------------------------------------------ common residues + AUC
common = sorted(r for r in labels if all(r in m for m in methods.values()))
y = np.array([labels[r] for r in common])
print(f"\ncommon residues: {len(common)} | interface: {int(y.sum())}\n")
print("residue-level ROC-AUC (identical labels):")
vecs = {}
for name, m in methods.items():
    vecs[name] = np.array([m[r] for r in common])
    print(f"  {name:12s}: {roc_auc_score(y, vecs[name]):.4f}")

print("\npairwise agreement (Spearman rho):")
for a_, b_ in itertools.combinations(methods, 2):
    print(f"  {a_:12s} vs {b_:12s}: {spearmanr(vecs[a_], vecs[b_]).correlation:.3f}")

K = int(y.sum())
true = {r for r in common if labels[r] == 1}
print(f"\ntrue interface residues recovered in each method's top-{K}:")
tops = {}
for name in methods:
    tops[name] = set(np.array(common)[np.argsort(-vecs[name])[:K]])
    print(f"  {name:12s}: {len(tops[name] & true)}/{K}")
shared_all = set.intersection(*tops.values())
print(f"\nresidues in ALL THREE methods' top-{K}: {len(shared_all)}")
