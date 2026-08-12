# pyamg-poisson-solve — provenance

A **self-verifying** `predict` task, and the first non-biology one: build an
algebraic-multigrid solver and return `x` solving `Ax = b`.

## Input

`input/` is a directory holding the whole system:

- `A.mtx` — a 625×625 2D five-point Poisson stencil (25×25 grid, Dirichlet boundaries,
  3025 nonzeros) in Matrix Market *coordinate real general* format.
- `b.txt` — the right-hand side, one value per line, drawn from `numpy` PCG64 seeded with
  `20260812`.

The submission writes `solution.csv` with `index,value` for every unknown `0..624`. Row
order doesn't matter; the evaluator scatters by index.

## Ground truth: there isn't a file, and that's the point

Nothing is withheld, because nothing needs to be. The score is

```
relative_residual = ‖Ax − b‖₂ / ‖b‖₂        pass if ≤ 1e-8
```

recomputed from the input every time. That makes this the **strongest kind of task in the
split**:

- **It cannot be contaminated.** There is no answer key to leak, publish, or accidentally
  commit — unlike the other four tasks, whose labels sit in this repo.
- **It is fully auditable.** Anyone can recompute the score from the input with fifteen
  lines of numpy. No trust in us is required.
- **It cannot be gamed by copying.** The registry publishes PyAMG's working contract, but
  the answer depends on *this* `b`, which no prior run has solved.

This is why `evaluation.self_verifying: true` exists as an explicit flag rather than just
an omitted `labels` field — it's a deliberate claim about how the task is graded, and
validation rejects a task that sets both.

## Calibration

A direct dense solve reaches **1.4e-15**, so the 1e-8 bar is nowhere near the numerical
limit. It matches the tolerance the original revival was held to, and it discriminates:
perturbing the exact solution by a uniform `1e-6` gives a residual of `4.2e-7` and fails.
A zero vector scores exactly 1.0.

## Why `dev`, not `test`

PyAMG is in the registry, so the *revival* is public even though the answer isn't. It is
also, unlike the other four, a repo that was never really dead — it's actively maintained
and JOSS-reviewed, which makes it a useful control: a submission that fails here has a
tooling problem, not a resurrection problem.

The task pattern, though, is the one to reuse for the held-out split. A self-verifying
target — a residual, an energy, a constraint that either holds or doesn't — is worth more
than any stored label, and cross-domain science is full of them.
