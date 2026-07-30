# Cross-domain decay measurement — methods (Track 2)

Agent-free measurement of computational-reproducibility decay across venues, comparing
**reviewed** vs **unreviewed** research software. Compute-light ($0, CPU-only); the counterpart
to the agent revival in the v1 preprint.

## Frames (seeded random samples, screened)
- **Reviewed arm — JOSS** (`benchmark/joss.py`): the Journal of Open Source Software publishes
  peer-reviewed *software*, cross-domain (astronomy, ML, chemistry, statistics, ecology, …), with
  the software repo as a first-class metadata field. Sample: `published.json` API → seeded shuffle
  → public-repo screen. Filtered to **primary language Python/R** (`--languages`) so one install
  ecosystem is held constant. Pool 2,436 (≥2018); **N=150**. (`benchmark/frame_joss.json`)
- **Unreviewed arm — regular journals** (`benchmark/frame_crossdomain.py`): venues that *link* a
  repo but do not review software for runnability. Europe PMC strata that pass abstract-extraction:
  BMC Bioinformatics, GigaScience, J. Cheminformatics. **N=112**. (`benchmark/frame_crossdomain.json`)
- Note: Crossref carries no repo for JOSS/SoftwareX (probe: 0%, `benchmark/crossref.py`); Papers
  With Code's dump is defunct. So the unreviewed arm is life-science-leaning (a stated limitation).

## Metric — install-decay (the robust signal)
Per repo, in a fresh container, following the repo's own files with **no repair** (`benchmark/baseline.py`):
clone → install (conda / pip / `pip install .` / R `DESCRIPTION`, first manifest wins) → attempt a
shipped example. `installed` is recorded tri-state:
- **True** — install succeeded (reached the example stage)
- **False** — install failed (real decay)
- **None** — `no_install_manifest` (not a standard package → N/A) or timeout/error (inconclusive)

Two reported quantities:
- **Packaging rate** = fraction that *are* an installable package (has a manifest).
- **Install-decay** = False / (True + False), i.e. among packages, the fraction that no longer install.

`naive_runs` (install **and** run a guessed example) is kept as a noisier secondary — it over-reports
decay when an example needs args/data/credentials, so it is **not** the headline metric.

## Environment
Docker on an x86 host. `continuumio/miniconda3` (Python), `rocker/r-ver:4.2.0` (R). For R the base
is enriched with common system libraries (`benchmark/r-sysdeps.Dockerfile` →
`lazarus/r-sysdeps:4.2.0`, via `baseline.py --r-image`): netCDF, git2, GDAL/GEOS/PROJ, image libs,
GLPK/GMP/GSL/NLopt. Rationale: a minimal R image penalises packages for missing *system* libs (an
environment deficiency, not decay); the enriched base isolates genuine decay. R install uses
`remotes::install_local(build=FALSE)` (tests installability, not vignette-building). A bounded,
retried, per-attempt-timeout watchdog enforces a 30-min per-repo cap.

## Failure-mode taxonomy (from hand-checking R failures)
- **syslib** — missing system library in the base image (environment; removed by the enriched base).
- **dep-rot** — a declared dependency is gone/unavailable (e.g. undocumented Bioconductor deps). *decay.*
- **compile-rot** — bundled C/C++ no longer compiles under the modern toolchain. *decay.*

## Results (enriched R base; Wilson 95% CIs) — scaled
| | N | packaging rate | install-decay (of packages) |
|---|---|---|---|
| JOSS (reviewed) | 173 | 95% | 37% [30–45] |
| EPMC (unreviewed) | 257 | 42% | 61% [51–70] |

- **Both contrasts are now significant** (two-proportion z-tests): packaging 95% vs 42%
  (z=11.1, p≪0.001); install-decay 37% vs 61% (**z=3.72, p=0.0002**, CIs now disjoint).
- **This required scaling** the arms past the original calibration frame (JOSS 150, EPMC 112),
  where install-decay was directional but underpowered (40% vs 52%, p=0.13 — the low EPMC packaging
  rate starves the *conclusive* denominator, so the very packaging gap that's significant also makes
  install-decay hard to power). We scaled EPMC to its 3-stratum ceiling (**257**, +145 disjoint) and
  JOSS to **173** (156 conclusive) — a two-stage seeded draw (pool shifted between draws; the union is
  a valid larger sample, deduped by repo_url). The EPMC arm is exhausted for these journals; reaching
  the full ~80%-power N (~587 EPMC) would need *more unreviewed journals* (a frame redefinition).
- Conclusive-N: JOSS 156, EPMC 102 (EPMC's 42% packaging is the binding constraint on n).
- Enriched-base correction (from the calibration frame): JOSS-R 53%→38% (5 syslib recoveries); EPMC-R genuine.
- Data: `benchmark/baseline_joss_scaled.json`, `benchmark/baseline_crossdomain_scaled.json` (calibration
  frames `benchmark/baseline_*_final.json` retained). Scale-up manifest `benchmark/frame_scaled_new.json`.

## Cross-domain revival pilot (companion to the decay measurement)
The decay study shows rot is broad; this pilot shows the **agent revives past biology**. We drew
**12 JOSS repos that were install-decay=False** (dead on their own install today), one per distinct
**non-bio** domain, and ran the *same* Track-1 agent harness (`benchmark/run.py`, identical config:
`--max-turns 90 --timeout 5400`, no `--model` override, independent smoke re-verification on, no
auto-land). Manifest: `benchmark/revival_crossdomain_repos.txt`; results: `benchmark/results_crossdomain.json`.

| metric | value |
|---|---|
| revived (installs + shipped example runs) | **11/12 = 92%** (Wilson [65–99]) |
| of which *reproduced* a reported number (±15%) | 4 (zodipy, PyBox, pySRURGS, AHGestimation) |
| independently verified by our own smoke re-run | 10/11 (+1 inconclusive — disruption-py, see verifier note) |
| not revived | 1 — RadGEEToolbox, **data-gated** on Google Earth Engine credentials (external auth, not decay/code) |

Domains covered: numerical linear algebra, astronomy, atmospheric chemistry, topology optimisation,
time-series decomposition, thermodynamics, symbolic regression, urban climate, plasma physics,
DFT/materials, remote sensing, and hydrology (**R** — the cross-language case). Total ≈ $10, ~median
$0.7/repo. w2w needed one retry (a transient Scout structured-output miss — `infra-failed`, retryable).

### Verifier correction (`interpret_smoke`)
Independent verification re-runs the emitted smoke and applies *our own* pass/fail (never the agent's).
The metric-threshold fallback (used when a smoke prints no explicit `PASS`/`FAIL` token) had two real
bugs that produced **false-negative** revivals, both now fixed with unit tests:
- **scientific notation** — the number regex `-?\d+(?:\.\d+)?` dropped exponents, so ssalib's
  `1.27e-15` (≪ 1e-6) parsed as `1.275` and failed. (Latent in pyamg/zodipy/w2w too, which passed
  only by an *accidental* cancellation of the two bugs.) Fixed to parse full sci-notation.
- **metric direction** — a single keyword list guessed lower-is-better and *defaulted the rest to
  higher-is-better*. Deviation-type metrics that matched no keyword (`aard`, `discordance`, …) were
  compared the wrong way (despasito's `AARD=0.033` and imputeqc's `discordance=0.018` read as fails).
  Replaced with **two explicit vocabularies** (lower- and higher-is-better); a metric matching
  **neither (or both) is `None` (inconclusive), never a confident False** — so a revival is never
  downgraded on a direction the instrument can't name.

Consequence, applied uniformly to both arms and validated against **every** metric (only the intended
verdicts moved): ssalib, despasito (JOSS) and imputeqc, GADMA (EPMC) re-verify correctly;
`peak_plasma_current_amps` (disruption-py) and `log_likelihood` (GADMA) have no nameable direction and
so read as **inconclusive** — their revivals stand (the values clear their floors), only the automatic
badge abstains. Crucially, `None` is *not* a free pass: **TAMPA** returns `None` only because its smoke
*crashed* (missing output PNG), so it is kept `runs-unverified`, not silently upgraded. The robust path
remains an explicit `PASS`/`FAIL` token in the smoke; the metric-threshold branch is the fallback.

## Cross-domain revival — UNREVIEWED arm (EPMC), the symmetric complement
The reviewed pilot shows revival works across domains; this arm tests the **venue/quality axis** on the
*harder* population. We took a **census of ALL 24 install-decay=False repos** in the unreviewed (EPMC)
frame — no sub-sampling, so no selection bias — and ran the **identical Track-1 instrument**.
Manifest `benchmark/revival_epmc_repos.txt`; data `benchmark/results_epmc_revival.json`. Life-science-
leaning by construction (a stated frame limitation): 18 Python / 6 R.

| | independently verified | revived (ran + produced a result) | reproduced a # | packaging rate |
|---|---|---|---|---|
| **Reviewed (JOSS)** | 10/12 = 83% | 11/12 = 92% | 4 | 94% |
| **Unreviewed (EPMC)** | 19/24 = 79% | 22/24 = 92% | 6 | 41% |

**The two arms are statistically indistinguishable** (Wilson CIs overlap heavily; "ran" is 92% vs 92%)
despite unreviewed software packaging **less than half as often**. Headline: *the reviewed/unreviewed
gap is packaging discipline, not resurrectability — once an agent is on the repo, peer review does not
predict whether the science comes back.* Full EPMC accounting (24, **no exclusions**): 19 verified ·
3 revived-inconclusive (GADMA clears its floor; SpheroScan/annotate could not be auto-confirmed) ·
1 `runs-unverified` (**TAMPA** — smoke errors, honestly counted as *not* a clean revival) ·
1 `budget-exceeded` (**DrGA** — a 90-min Bioconductor compile that ran past the per-repo cap). cmmrt
took **3 attempts** (the first two were mid-Scout connection drops on the operator side, `infra-failed`/
retryable; the third got a fair attempt and *reproduced*, pearson_r=1.0). Cost ≈ $43 (≈ $53 both arms). Two mid-run robustness notes: `docker commit` briefly `(Paused)`s a container (benign,
not a host suspend); and the per-repo wall-clock watchdog counts a paused container's time as elapsed.

## Limitations
Small-ish N (wide CIs); JOSS packaging rate is partly by-construction (JOSS *requires* packaged
software); unreviewed arm is life-science-leaning; "installs in a standard env" penalises packages
with undocumented system deps (arguably itself a reproducibility gap); single run (agent-free, so
deterministic modulo network); domain-matched bio sub-cut is underpowered (JOSS-bio N≈12). The
revival arms are a single run per repo (reviewed N=12, unreviewed N=24; wide, overlapping CIs) and,
like Track-1, the success bar is "installs + a shipped example runs and we re-verify it," not a full
scientific reproduction. The reviewed arm is a *purposive* one-per-domain draw (biases the rate up,
good for the generalisation claim, not for a rate); the unreviewed arm is a *census* of its frame (no
selection bias) but life-science-leaning. The reviewed↔unreviewed comparison mixes domain and venue
(the unreviewed arm is not domain-matched to JOSS), so it speaks to *venue*, not domain. Automatic
verification abstains (`inconclusive`) on metrics whose direction it cannot name from the metric name.
