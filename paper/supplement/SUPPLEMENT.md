# Supplementary tables — cross-domain reproducibility & revival
Four supplementary tables (full per-repo data as CSV in this directory):
- **S1** `S1_decay_reviewed_JOSS.csv` — decay corpus, reviewed (JOSS), N=173
- **S2** `S2_decay_unreviewed_EPMC.csv` — decay corpus, unreviewed (Europe PMC), N=257
- **S3** `S3_revival_reviewed_crossdomain.csv` — revival arm, reviewed cross-domain, N=12
- **S4** `S4_revival_unreviewed.csv` — revival arm, unreviewed census, N=24

The Track-1 biology revival benchmark (N=20, Bioinformatics 2018–2021) is reported in the v1 preprint; it is the biology counterpart to S3/S4.

## In-text summary — decay (agent-free install-decay; enriched R base)
| corpus | N | packaging rate | install-decay (of packages) |
|---|---|---|---|
| Reviewed (JOSS) | 173 | 95% [90–97] | 37% [30–45] |
| Unreviewed (EPMC) | 257 | 42% [36–48] | 61% [51–70] |

Packaging 95% vs 42% (two-proportion z=11.1, p≪0.001); install-decay 37% vs 61% (z=3.72, p=0.0002). Conclusive-n: JOSS 156, EPMC 102.

## In-text summary — revival (agent; success bar = installs + shipped example runs, independently smoke-verified)
| outcome | reviewed cross-domain (N=12) | unreviewed census (N=24) |
|---|---|---|
| reproduced | 4 | 6 |
| revived (verified) | 6 | 13 |
| revived (inconclusive) | 1 | 3 |
| runs-unverified | 0 | 1 |
| budget-exceeded | 0 | 1 |
| data-gated | 1 | 0 |

Ran (installed + example ran): reviewed 11/12 = 92%; unreviewed 22/24 = 92%. Independently verified: reviewed 10/12 = 83%; unreviewed 19/24 = 79%. Statistically indistinguishable across arms.
