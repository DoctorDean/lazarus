# Reproduction certificate — meirlop_motif_enrichment

> Reproduce shipped reference: MA0139.1 CTCF logistic-regression AUC on 235,220 DHS scored sequences (notebooks/meirlop_output_directory/lr_results.tsv, rank-1 motif).

| | |
|---|---|
| Metric | `roc_auc` |
| Paper reports | **0.7814** (notebooks/meirlop_output_directory/lr_results.tsv) |
| Lazarus measured | **0.7814194753559087 (n=235220)** |
| Tolerance | ±0.001 |
| Verdict | **REPRODUCED ✓** |

Reproduce it yourself:

```bash
meirlop --covariates notebooks/covariates.tsv --scan --fa notebooks/scored_fasta.fa notebooks/ctcf_motifs.txt out/
```
