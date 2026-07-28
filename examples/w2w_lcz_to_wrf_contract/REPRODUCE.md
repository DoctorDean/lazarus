# Reproduction certificate — w2w_lcz_to_wrf

> Regenerated geo_em.d04_LCZ_params.nc FRC_URB2D urban-fraction field vs. the reference file committed in sample_data/.

| | |
|---|---|
| Metric | `max_abs_diff_FRC_URB2D` |
| Paper reports | **0** (repo sample_data/geo_em.d04_LCZ_params.nc (Zaragoza)) |
| Lazarus measured | **5.96e-08 (n=16524)** |
| Tolerance | ±0.0001 |
| Verdict | **REPRODUCED ✓** |

Reproduce it yourself:

```bash
w2w ./sample_data lcz_zaragoza.tif geo_em.d04.nc
```
