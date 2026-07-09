"""Fair head-to-head: MaSIF-site vs ScanNet on PD-L1 (4ZQK chain A), residue level.

Both methods are scored against the SAME ground truth: chain-A residues with any heavy
atom within 5.0 Å of the partner chain in the 4ZQK complex.

Usage:
    python analysis/compare_masif_scannet.py <artifacts_dir>

<artifacts_dir> must contain (extracted with `docker cp` from the resurrected snapshots,
see analysis/RESULTS.md):
    4ZQK.pdb                          # the full complex (chains A=PD-L1, B=PD-1)
    masif/pred_4ZQK_A.npy             # MaSIF per-vertex interaction-site scores
    masif/p1_X.npy p1_Y.npy p1_Z.npy  # MaSIF per-vertex coordinates
    masif/p1_iface_labels.npy         # MaSIF's own per-vertex ground-truth labels (sanity)
    scannet/predictions_4ZQK_A.csv    # ScanNet per-residue binding-site probabilities

Requires: numpy, scipy, scikit-learn, biopython.
"""
import csv
import os
import sys

import numpy as np
from Bio.PDB import NeighborSearch, PDBParser
from Bio.PDB.Polypeptide import is_aa
from scipy.spatial import cKDTree
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

S = sys.argv[1] if len(sys.argv) > 1 else "artifacts"
CHAIN = "A"
CUTOFF = 5.0

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

# ------------------------------------------------------------------ MaSIF (vertex -> residue)
scores = np.load(os.path.join(S, "masif", "pred_4ZQK_A.npy")).reshape(-1)
verts = np.stack([np.load(os.path.join(S, "masif", f"p1_{c}.npy")) for c in "XYZ"], axis=1)
_, nn = tree.query(verts)
vert_res = np.array(a_resid)[nn]
masif = {}
for rid, sc in zip(vert_res, scores):
    masif.setdefault(int(rid), []).append(float(sc))
masif = {r: max(v) for r, v in masif.items()}   # residue score = max over its vertices

vlab = np.load(os.path.join(S, "masif", "p1_iface_labels.npy"))
print(f"[sanity] MaSIF vertex-level ROC-AUC vs shipped labels: {roc_auc_score(vlab, scores):.4f}")

# ------------------------------------------------------------------ fair comparison
common = sorted(r for r in labels if r in scannet and r in masif)
y = np.array([labels[r] for r in common])
m = np.array([masif[r] for r in common])
s = np.array([scannet[r] for r in common])
print(f"\ncommon residues: {len(common)} | interface: {int(y.sum())}")
print(f"  MaSIF-site residue-level ROC-AUC : {roc_auc_score(y, m):.4f}")
print(f"  ScanNet    residue-level ROC-AUC : {roc_auc_score(y, s):.4f}")

K = int(y.sum())
top_m = set(np.array(common)[np.argsort(-m)[:K]])
top_s = set(np.array(common)[np.argsort(-s)[:K]])
true = {r for r in common if labels[r] == 1}
print("\nagreement:")
print(f"  Spearman rho          : {spearmanr(m, s).correlation:.3f}")
print(f"  top-{K} shared/Jaccard : {len(top_m & top_s)} / {len(top_m & top_s) / len(top_m | top_s):.3f}")
print(f"  MaSIF top-{K} true     : {len(top_m & true)}/{K}")
print(f"  ScanNet top-{K} true   : {len(top_s & true)}/{K}")
