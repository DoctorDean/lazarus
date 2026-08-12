# deepdta-davis-ci — provenance

The split's only `reproduce` task. Its real job is to be the **worked example of verifying a
paper number**, because §2.4 established that the recorded `reproduced_reported` values
cannot be lifted without checking each one.

## The target, and how it was verified

**Concordance Index = 0.878 on the Davis dataset**, for the CNN-CNN configuration.

Not taken from `results*.json`. Read out of the paper's own results table via the Europe
PMC open-access full text ([PMC6129291](https://europepmc.org/article/MED/30423097), doi
`10.1093/bioinformatics/bty593`):

```
                          Proteins  Compounds     CI (std)     MSE
KronRLS  (Pahikkala 2014)  S–W      Pubchem Sim   0.871 (0.0008)  0.379
SimBoost (He 2017)         S–W      Pubchem Sim   0.872 (0.002)   0.282
DeepDTA                    S–W      Pubchem Sim   0.790 (0.009)   0.608
DeepDTA                    CNN      Pubchem Sim   0.835 (0.005)   0.419
DeepDTA                    S–W      CNN           0.886 (0.008)   0.420
DeepDTA                    CNN      CNN           0.878 (0.004)   0.261
```

confirmed by the prose: *"This method performed as well as the baseline methods with CI
score of 0.878 on the Davis dataset."*

Two things fall out of reading the source that reading the results file would never have
given us: **which row** the number belongs to (CNN-CNN, not the S–W/CNN row at 0.886), and
the paper's **own reported standard deviation, 0.004**.

## Why the tolerance is 0.03, not the 0.15 default

The harness default is a ±15% relative band. On this target that means:

| rel_tol | band | admits the paper's own weaker ablations? |
|---|---|---|
| 0.15 (default) | [0.746, 1.010] | 0.790 ✓ and 0.835 ✓ — **both** |
| 0.05 | [0.834, 0.922] | 0.835 ✓ |
| **0.03 (used)** | **[0.852, 0.904]** | **neither** |

A 15% band would pass configurations the paper itself reports as *worse*, and an upper
bound above 1.0 for a metric that cannot exceed 1.0. It would certify "reproduced" for
almost any working DTA model. At 0.03 the band is still ~6.5× the paper's own std, so it
absorbs environment and framework drift, while excluding the ablations.

The general lesson for the remaining `check-paper` candidates: **the tolerance is part of
the verification, not a default to inherit.** A band has to be set against the spread the
paper reports and the neighbouring results it must exclude.

## Output

No harness input — the Davis dataset ships in the repo, which is what makes this a
reproduction rather than a prediction. The submission writes `result.txt` containing:

```
concordance_index=0.87…
```

The `scalar` grader requires the metric to be **labelled**. A raw training log with several
numbers in it is refused as ambiguous rather than guessed at, so a submission cannot get
credit by printing many numbers and hoping one lands in the band.

## Why `reproduce` is dev-only

The test split is `predict`-only by decision: a `reproduce` target is printed in the paper,
so it can be looked up rather than computed, and a submission could hard-code it without
running anything. This task exists so the kind, the two-sided band and the `scalar` grader
have one real exercise — and so the verification procedure above is written down somewhere
before it's needed at scale.
