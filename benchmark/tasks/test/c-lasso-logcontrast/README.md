# c-lasso-logcontrast — provenance

The **first held-out `test`-split task** (P3). A **self-verifying** `predict` task: revive
[c-lasso](https://github.com/Leo-Simpson/c-lasso) and solve its standard constrained-Lasso
problem, graded by KKT optimality recomputed from the input.

## Why it's eligible for the test split

- **Fresh.** Mined by `mine_test_candidates.py` from the disjoint pool; c-lasso is not in
  the attempted corpus (`tasks/pins.json`) or the registry, so no answer is a `docker pull`.
- **Pinned before us.** `82b106c4` (2021-05-05), recorded in `tasks/test_pins.json`.
- **Dead today.** `lazarus decay-check` marks it DECAYED at HEAD (`tasks/test_decay.json`);
  the pinned 2021 tree is at least as dead.
- **Self-verifying**, so — as with `pyamg-poisson-solve` — there is no label to withhold,
  leak, or accidentally commit. The whole task, input included, is public and auditable.

## The problem

c-lasso's R1 formulation, with **no** `1/2` or `1/n` factor on the least-squares term:

```
argmin_b  ||X b - y||^2  +  lambda * ||b||_1     s.t.   C b = 0
```

`C` is the single zero-sum / log-contrast row (`1^T b = 0`), the constraint c-lasso exists
to handle (compositional data). To match this exactly, configure c-lasso with
`concomitant = False` and `rescaled_lam = False` (so `lambda` is absolute, not `lambda /
lambda_max`).

## Input

`input/` holds the whole instance, dense whitespace text, regenerable byte-for-byte by
`make_input.py` (seed `20260918`):

- `X.txt` — design matrix, 64×32, columns centred.
- `y.txt` — response, 64 values, one per line.
- `C.txt` — constraint, 1×32 row of ones.
- `lambda.txt` — the penalty, `25.0` (≈ `0.1 * lambda_max`, giving a ~5-nonzero solution).

The submission writes `beta.csv` with `index,value` for every coefficient `0..31`. Row
order doesn't matter.

## Ground truth: there isn't a file

The score is the worst **KKT-optimality violation**, recomputed from `X, y, C, lambda`
every time (`evaluators.kkt_residual`). For `g = 2 X^T (X b - y)` and a dual `nu` for
`C b = 0`, an optimum satisfies `g_i + lambda*sign(b_i) + (C^T nu)_i = 0` on the support,
`|g_i + (C^T nu)_i| <= lambda` off it, and `C b = 0`; the residual is the largest breach,
normalised by `lambda` (feasibility by `||b||_1`) so it is dimensionless.

## Calibration

Against an independent ADMM solve (numpy, not c-lasso):

| submission | kkt_residual |
|---|--:|
| the optimum | ~1e-15 |
| a loosely-converged (200-iter) but valid solve | 4.7e-3 |
| optimum + 1% noise | 1.8 |
| unconstrained OLS | 1.2 |
| zero vector | 9.1 |
| solved at 2·lambda (a convention slip) | 1.0 |

The **1e-2** bar clears a well-converged solve with ~50× margin while rejecting every
wrong or wrong-`lambda` answer — including the failure mode that matters most here, an
agent that revives c-lasso but leaves it on a different `lambda` convention.

## Achievability

The evaluator is validated (`tests/test_tasks.py`), but the number a real revived c-lasso
actually reaches has **not yet been measured** — that is the achievability run (revive at
the pinned SHA, solve, grade). If c-lasso's solver is looser than 1e-2 the threshold is
relaxed then; the task is not final until a genuine revival is shown to pass.
