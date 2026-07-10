# Reproduction certificate — diffdock_blind_docking

> DiffDock-L top-1 success rate (fraction of complexes with top-1 pose RMSD < 2.0 A) on the repo's own PDBBind test set. Reported ~38-43%. On an 8-complex sample drawn from data/testset_csv.csv, 3/8 top-1 poses were < 2.0 A (6moa 0.34, 6e4c 1.56, 6jsn 1.70), consistent with the reported rate; confidence tracked RMSD (positive-confidence poses were the accurate ones).

| | |
|---|---|
| Metric | `top1_success_rate_rmsd_lt_2A` |
| Paper reports | **0.4** (DiffDock / DiffDock-L (ICLR 2023 + 2024 update); repo data/testset_csv.csv) |
| Lazarus measured | **0.375 (n=8)** |
| Tolerance | ±0.15 |
| Verdict | **REPRODUCED ✓** |

Reproduce it yourself:

```bash
micromamba run -n diffdock python inference.py --protein_ligand_csv lazarus_bench/batch.csv --out_dir OUT --model_dir ./workdir/v1.1/score_model --confidence_model_dir ./workdir/v1.1/confidence_model --samples_per_complex 10; then lazarus_eval_batch.py
```
