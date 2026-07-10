# Reproduction certificate — basset_predict

> Full ENCODE+Roadmap held-out test set: mean AUROC across the 164 cell-type targets, using the official basset_test.lua. Test sequences re-encoded from the local encode_roadmap.fa with the uppercasing fix so soft-masked bases are not dropped.

| | |
|---|---|
| Metric | `mean AUROC across 164 targets` |
| Paper reports | **0.895** (Kelley et al., Genome Research 2016 (reports ~0.895 mean AUC)) |
| Lazarus measured | **0.8944 (n=71886)** |
| Tolerance | ±0.02 |
| Verdict | **REPRODUCED ✓** |

Reproduce it yourself:

```bash
source /etc/profile.d/basset.sh && cd $BASSETDIR && th src/basset_test.lua data/models/pretrained_model.th data/encode_roadmap_test_fixed.h5 test_out_fixed && awk '{s+=$2;n++} END{printf "mean_auroc=%.4f\n",s/n}' test_out_fixed/aucs.txt
```
