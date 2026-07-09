# Reproduction certificate — masif_site

> MaSIF-site transient PPI benchmark — median per-structure interaction-site ROC-AUC

| | |
|---|---|
| Metric | `median_roc_auc` |
| Paper reports | **0.85** (Gainza et al., Nat. Methods 2020; transient test set (full n=59)) |
| Lazarus measured | **0.82 (n=15)** |
| Tolerance | ±0.05 |
| Verdict | **REPRODUCED ✓** |

Reproduce it yourself:

```bash
cd /masif/data/masif_site && bash reproduce_transient_benchmark.sh   # this run: first 15 of lists/testing_transient.txt
```
