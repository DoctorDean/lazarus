# Head-to-head: MaSIF-site vs ScanNet vs dMaSIF on PD-L1 (4ZQK chain A)

Three dead binding-site methods, each [resurrected autonomously by Lazarus](../README.md),
scored against **identical residue labels** on the same protein.

## Ground truth

PD-L1 (4ZQK chain A) has **115 amino-acid residues**; **22** are interface residues,
defined as having any heavy atom within **5.0 Å** of the partner chain (PD-1) in the
4ZQK complex.

## Result

Scored by a single script ([`compare_three_way.py`](compare_three_way.py)) on the
**104 residues all three methods cover** (22 interface):

| Method | Representation | Residue-level ROC-AUC |
|---|---|:--:|
| **ScanNet** | native per-residue | **0.915** |
| **dMaSIF** | per-point → per-residue | **0.854** |
| **MaSIF-site** | per-vertex → per-residue | **0.823** |
| *MaSIF-site (native vertex-level)* | *per-vertex* | *0.914* |

**Pairwise agreement (Spearman ρ)**

| Pair | ρ |
|---|:--:|
| **dMaSIF ↔ MaSIF-site** (both surface methods) | **0.70** |
| ScanNet ↔ dMaSIF | 0.51 |
| ScanNet ↔ MaSIF-site | 0.43 |

**Consensus:** 13 residues appear in *all three* methods' top-22 predictions.

## Reading

- **All three independently localize the PD-1/PD-L1 interface** — the headline. A
  13-residue core is called by every method.
- The structure of the *disagreement* is meaningful: the two **surface** methods (MaSIF
  and its differentiable successor dMaSIF) correlate most strongly with each other
  (ρ 0.70), while **ScanNet** — which works from atoms/residues, not a molecular surface —
  is the outlier. Method family shows up in the numbers.
- At residue resolution ScanNet leads; MaSIF is a surface method whose native vertex-level
  score is **0.914** — collapsing a surface to residues costs resolution.
- Validation: the script recomputes MaSIF's vertex-level ROC-AUC as **0.9137**, an exact
  match to the resurrection's reported value.

## Reproduce

Per-structure artifacts were extracted from the three Bertha snapshots with `docker cp`:

```bash
export DOCKER_HOST=ssh://<user>@<x86-host>          # where the snapshots live
mkdir -p artifacts/masif artifacts/scannet artifacts/dmasif

# MaSIF
mid=$(docker create lazarus/masif:site-ready); P=/masif/data/masif_site
docker cp "$mid:$P/output/all_feat_3l/pred_data/pred_4ZQK_A.npy" artifacts/masif/
for a in p1_X p1_Y p1_Z p1_iface_labels; do
  docker cp "$mid:$P/data_preparation/04a-precomputation_9A/precomputation/4ZQK_A/$a.npy" artifacts/masif/
done
docker cp "$mid:$P/data_preparation/00-raw_pdbs/4ZQK.pdb" artifacts/; docker rm "$mid"

# ScanNet
sid=$(docker create lazarus/scannet:ppi-noMSA-proven)
docker cp "$sid:/ScanNet/predictions/4ZQK_A_(0-A)_single_ScanNet_interface_noMSA/predictions_4ZQK_A.csv" artifacts/scannet/
docker rm "$sid"

# dMaSIF (GPU) — run predict then copy the per-residue arrays
cid=$(docker run -d --gpus all lazarus/dmasif:site-ready sleep infinity)
docker exec "$cid" bash -lc 'export KEOPS_CACHE_FOLDER=/root/keops_cache; cd /root/MaSIF_colab && python predict_site.py examples/4ZQK.pdb /root/out A cuda:0'
docker cp "$cid:/root/out/." artifacts/dmasif/; docker rm -f "$cid"

python analysis/compare_three_way.py artifacts
```
