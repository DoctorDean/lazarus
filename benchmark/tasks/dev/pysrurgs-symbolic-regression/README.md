# pysrurgs-symbolic-regression — provenance

A `predict` task in a third domain: fit a symbolic expression to a numeric dataset, then
predict unseen points.

## Input

`input/` holds both halves of the problem:

- `train.csv` — 120 rows of `x0, x1, y`.
- `test.csv` — 60 rows of `id, x0, x1`. Features only; the targets are withheld.

The submission writes `prediction.csv` with `id, score` for all 60 test ids.

## Ground truth

`labels/test_y.csv` — the withheld targets, from a **noiseless closed-form function of two
variables**, evaluated on inputs drawn uniformly from `[-3, 3]²` with `numpy` PCG64 seeded
`20260812`. The function is not printed here; it is recoverable exactly, so the ceiling is
`R² = 1.0`.

Synthetic data is not a compromise in this field — symbolic-regression methods are
conventionally benchmarked on known closed forms, precisely because you can tell whether
the *structure* was recovered rather than curve-fitted. It also means this task is
generated fresh: the registry publishes pySRURGS's working contract, but no prior run has
fitted this system.

## Calibration

The bar is set to discriminate, not to be generous. Measured on the actual data:

| submission | R² | verdict |
|---|---|---|
| exact function | 1.0000 | pass |
| correct form, 3% coefficient error | 0.9983 | pass |
| **best possible linear fit** | **0.1068** | fail |
| predict the training mean | −0.0013 | fail |

`0.90` therefore cannot be reached without recovering the non-linear structure, while a
correct-but-imprecise fit still passes — which is the right shape for a *revival* test,
where the question is "does the method work" rather than "is it state of the art". The
original revival was held to `r_squared ≥ 0.99` on its own data.

R² is deliberately **not clipped at zero**: a model worse than the mean scores negative, and
flattening that to 0 would make a broken submission look merely mediocre.

## Why `dev`, not `test`

pySRURGS is in the Lazarus registry, so the revival recipe is public even though this
dataset is new. Note also that the task is *stochastic by design* — uniform random global
search will not return the same expression twice — so it exercises the same repeat-variance
question the DiffDock task raises, in a domain where it's intrinsic rather than incidental.
