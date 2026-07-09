# Head-to-head: MaSIF-site vs ScanNet on PD-L1 (4ZQK chain A)

Two dead binding-site methods, each [resurrected autonomously by Lazarus](../README.md),
scored against **identical residue labels** on the same protein.

## Ground truth

PD-L1 (4ZQK chain A) has **115 amino-acid residues**; **22** are interface residues,
defined as having any heavy atom within **5.0 Å** of the partner chain (PD-1) in the
4ZQK complex.

## Result

Scored on the **104 residues both methods cover** (22 of them interface):

| Method | Representation | ROC-AUC |
|---|---|:--:|
| ScanNet | native per-residue | **0.915** |
| MaSIF-site | per-vertex → per-residue (max) | **0.823** |
| MaSIF-site | native per-vertex | **0.914** |

**Agreement between the two methods**

| Metric | Value |
|---|:--:|
| Spearman ρ (per-residue scores) | 0.43 |
| Shared calls in each method's top-22 | 16 |
| True interface in MaSIF top-22 | 13 / 22 |
| True interface in ScanNet top-22 | 16 / 22 |

## Reading

- **Both methods correctly localize the PD-1/PD-L1 interface** — the headline. They agree
  on its core (16 shared top calls) and differ at the edges, as two genuinely independent
  models should.
- At **residue** resolution ScanNet (natively per-residue) edges MaSIF; but MaSIF is a
  **surface** method whose native vertex-level score is **0.914** — collapsing a surface
  to residues costs resolution. Each is strongest in its own representation.
- Validation: the script recomputes MaSIF's vertex-level ROC-AUC as **0.9137**, an exact
  match to the value the resurrection reported — so the extraction and residue mapping are
  correct.

## Reproduce

The per-structure artifacts were extracted from the two Bertha snapshots with `docker cp`:

```bash
export DOCKER_HOST=ssh://<user>@<x86-host>       # where the snapshots live
mkdir -p artifacts/masif artifacts/scannet

mid=$(docker create lazarus/masif:site-ready)
P=/masif/data/masif_site
docker cp "$mid:$P/output/all_feat_3l/pred_data/pred_4ZQK_A.npy" artifacts/masif/
for a in p1_X p1_Y p1_Z p1_iface_labels; do
  docker cp "$mid:$P/data_preparation/04a-precomputation_9A/precomputation/4ZQK_A/$a.npy" artifacts/masif/
done
docker cp "$mid:$P/data_preparation/00-raw_pdbs/4ZQK.pdb" artifacts/
docker rm "$mid"

sid=$(docker create lazarus/scannet:ppi-noMSA-proven)
docker cp "$sid:/ScanNet/predictions/4ZQK_A_(0-A)_single_ScanNet_interface_noMSA/predictions_4ZQK_A.csv" artifacts/scannet/
docker rm "$sid"

python analysis/compare_masif_scannet.py artifacts
```
