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

## Results (enriched R base; Wilson 95% CIs)
| | N | packaging rate | install-decay (of packages) |
|---|---|---|---|
| JOSS (reviewed) | 150 | 94% [89–97] | 40% [32–48] |
| EPMC (unreviewed) | 112 | 41% [32–50] | 52% [38–66] |

- **Packaging rate is the clean, significant result** (CIs disjoint). Install-decay-among-packages
  overlaps (40 vs 52) — directional, not significant at this N.
- By language (install-decay): JOSS py 40% / r 38%; EPMC py 47% / r 75%.
- Enriched-base correction: JOSS-R 53%→38% (5 syslib recoveries); EPMC-R 75%→75% (all genuine).
- Merged final data: `baseline_joss_final.json`, `baseline_crossdomain_final.json` (R rows = enriched).

## Cross-domain revival pilot (companion to the decay measurement)
The decay study shows rot is broad; this pilot shows the **agent revives past biology**. We drew
**12 JOSS repos that were install-decay=False** (dead on their own install today), one per distinct
**non-bio** domain, and ran the *same* Track-1 agent harness (`benchmark/run.py`, identical config:
`--max-turns 90 --timeout 5400`, no `--model` override, independent smoke re-verification on, no
auto-land). Manifest: `benchmark/revival_crossdomain_repos.txt`; results: `benchmark/results_crossdomain.json`.

| metric | value |
|---|---|
| revived (installs + shipped example runs, WE re-verify the smoke) | **11/12 = 92%** (Wilson [65–99]) |
| of which *reproduced* a reported number (±15%) | 4 (zodipy, PyBox, pySRURGS, AHGestimation) |
| independently verified by our own smoke re-run | 11/11 |
| not revived | 1 — RadGEEToolbox, **data-gated** on Google Earth Engine credentials (external auth, not decay/code) |

Domains covered: numerical linear algebra, astronomy, atmospheric chemistry, topology optimisation,
time-series decomposition, thermodynamics, symbolic regression, urban climate, plasma physics,
DFT/materials, remote sensing, and hydrology (**R** — the cross-language case). Total ≈ $10, ~median
$0.7/repo. w2w needed one retry (a transient Scout structured-output miss — `infra-failed`, retryable).

### Verifier correction (`interpret_smoke`)
Independent verification (the harness re-runs the emitted smoke and applies *its own* pass/fail, never
the agent's) initially mis-scored **ssalib** and **despasito** as `runs-unverified`. Both were
**false negatives** from two real bugs in `interpret_smoke`, now fixed (+ unit tests):
- **scientific notation** — the number regex `-?\d+(?:\.\d+)?` dropped exponents, so ssalib's
  `1.27e-15` (≪ 1e-6) parsed as `1.275` and failed. (Also latent in pyamg/zodipy/w2w, which passed
  only by an *accidental* cancellation of both bugs.)
- **metric direction** — lower-is-better was inferred from the metric name; deviation-type metrics
  (`aard`, `diff`, `residual`, `deviation`) matched no keyword and were treated as higher-is-better,
  so despasito's excellent `AARD=0.033` read as a fail against a `≤0.15` bar.
Fix validated by re-running every pilot smoke and confirming *no* other verdict changed; both repos
re-verify True and are re-scored to `revived`. The robust path remains an explicit `PASS`/`FAIL` token
in the smoke (which most emitted smokes print); the metric-threshold branch is the fragile fallback.

## Limitations
Small-ish N (wide CIs); JOSS packaging rate is partly by-construction (JOSS *requires* packaged
software); unreviewed arm is life-science-leaning; "installs in a standard env" penalises packages
with undocumented system deps (arguably itself a reproducibility gap); single run (agent-free, so
deterministic modulo network); domain-matched bio sub-cut is underpowered (JOSS-bio N≈12). The
revival pilot is a single run per repo (N=12, wide CI) and, like Track-1, its success bar is
"installs + a shipped example runs and we re-verify it," not a full scientific reproduction.
