# Reproduction certificate — matador_kp_convex_hull

> Published K-P binary convex hull distances reproduced from 295 shipped DFT .res structures via matador.hull.QueryConvexHull.

| | |
|---|---|
| Metric | `max_abs_error_vs_reference_eV_per_atom` |
| Paper reports | **0** (repo tests/data/test_KP_hull_dist.dat (test_binary_hull_distances)) |
| Lazarus measured | **0 (n=295)** |
| Tolerance | ±0.001 |
| Verdict | **REPRODUCED ✓** |

Reproduce it yourself:

```bash
cd /root/repo && python prove_kp_hull.py
```
