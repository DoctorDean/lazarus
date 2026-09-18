#!/usr/bin/env python3
"""Generate the fixed input for the c-lasso-logcontrast test task. Committed for provenance:
the task IS the four files this writes, and the grader (evaluators.kkt_residual) recomputes
the score from them, so nothing here is an answer key — re-running it reproduces the input
byte-for-byte from the seed.

    python benchmark/tasks/test/c-lasso-logcontrast/make_input.py

Problem (c-lasso R1, the standard constrained Lasso):

    argmin_b  ||X b - y||^2  +  lam ||b||_1    s.t.   C b = 0

with C the single zero-sum / log-contrast row (1^T b = 0). numpy only, no scipy: a task's
input should have as few moving parts as its grader.
"""
from pathlib import Path
import numpy as np

SEED, N, P, K, NOISE, LAM = 20260918, 64, 32, 6, 0.05, 25.0
HERE = Path(__file__).resolve().parent
OUT = HERE / "input"


def make():
    rng = np.random.default_rng(SEED)
    X = rng.standard_normal((N, P))
    X -= X.mean(0)                       # centre columns, as for compositional/log-contrast data
    beta_true = np.zeros(P)
    idx = rng.choice(P, size=K, replace=False)
    vals = rng.standard_normal(K)
    vals -= vals.mean()                  # true support is itself zero-sum
    beta_true[idx] = vals
    y = X @ beta_true + NOISE * rng.standard_normal(N)
    C = np.ones((1, P))
    return X, y, C


def write(X, y, C):
    OUT.mkdir(parents=True, exist_ok=True)
    # dense whitespace matrices/vectors; %.17g round-trips a float64 exactly
    (OUT / "X.txt").write_text(
        "\n".join(" ".join(f"{v:.17g}" for v in row) for row in X) + "\n")
    (OUT / "y.txt").write_text("\n".join(f"{v:.17g}" for v in y) + "\n")
    (OUT / "C.txt").write_text(
        "\n".join(" ".join(f"{v:.17g}" for v in row) for row in C) + "\n")
    (OUT / "lambda.txt").write_text(f"{LAM:.17g}\n")


if __name__ == "__main__":
    X, y, C = make()
    write(X, y, C)
    print(f"wrote {OUT}: X {X.shape}, y {y.shape}, C {C.shape}, lambda={LAM}")
