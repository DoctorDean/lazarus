# Changelog

All notable changes to Lazarus (`lazarus-bio`) are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/).

## [Unreleased]

The Tier-1 **flagship** from the roadmap: *real science from resurrected bricks*. Unlike 0.4.0,
this one **does** change the installed package — the two runner fixes below are what make a
pipeline like this composable at all, so they need a release to reach users.

### Added
- **`target_dock_consensus`** (`pipelines/`) — a four-brick pipeline that triangulates a druggable
  small-molecule site and cross-validates it against a crystal ligand: fpocket (2010 C, geometry) +
  ScanNet (learned, PPI-site) + DiffDock (2023, generative, GPU) + EquiBind (generative, CPU) into
  one consensus adapter. Verified end-to-end on **BRD2's BD2 bromodomain (PDB 6MOA)**: druggability
  **0.93**, ScanNet quiet (mean p **0.26**), both dockers in-pocket at **0.20 Å** / **0.84 Å** from
  the crystal-ligand centroid, both converging on **Asn429** + **Trp370** — the real BET
  pharmacophore. Verdict: *CONFIRMED small-molecule site*, the mirror image of the PD-L1 pipeline's
  *flat interface / biologic target*.
- Two new stdlib+numpy bricks: **`dock_prep`** (split a complex into receptor + reference ligand +
  DiffDock CSV) and **`dock_site_consensus`** (the fusion: pose → contact residues, overlap with the
  druggable pocket and the predicted site, pose-vs-crystal and pose-vs-pose geometry).
- **`pipelines/sample_output_6MOA/`** — the committed run: every output artifact, the exact command,
  input provenance, and an explicit note on what reproduces exactly (fpocket, ScanNet, EquiBind) vs.
  what moves run to run (DiffDock is generative — two runs gave 0.20 Å / 0.22 Å).
- 17 new tests (74 → 91): regression cover for both runner fixes, a parity check that each adapter's
  `.py` still matches the copy embedded in its contract, and unit cover for the adapters' parsing,
  geometry, and all three verdict branches (confirmed / PPI / inconclusive).

### Fixed
- **Nested step artifacts now resolve.** `${step.selector}` globs recursively and matches files
  only, so an output like DiffDock's `$OUTDIR/<complex_name>/rank1.sdf` is found and a
  same-named directory can't shadow it.
- **Bricks that run as a non-root user can now be composed.** The shared `/lazarus` work dirs are
  created as root and made world-writable, so images with their own user (DiffDock's `appuser`) can
  read staged inputs and write outputs; `Sandbox.exec` gained a `user=` argument.
- `dock_prep` writes the DiffDock CSV's `protein_path` as the absolute in-container receptor path.

## [0.4.0] — 2026-07-28

A **registry + evidence** milestone. The installed `lazarus-bio` package is *unchanged* from
0.3.0 — the new tools reach users live via the registry, so there's nothing to `pip install`.
See the [v0.4.0 GitHub Release](https://github.com/DoctorDean/lazarus/releases) for the full write-up.

### Added
- **Registry grew 13 → 25 (23 pullable from GHCR).** Twelve new cross-domain revivals published and
  wired in: PyAMG (numerical LA), matador (materials/DFT), DESPASITO (thermodynamics), AHGestimation
  (hydrology), Scikit-Topt (topology opt.), SSALib (time-series), W2W (urban climate), AiZynthFinder
  (retrosynthesis), MEIRLOP, PRODIGY-CRYSTAL, DeepFRI, trRosetta — plus Basset, now published.
  (dMaSIF and Sequoya stay rebuild-locally — license and image size.)
- **Cross-domain reproducibility study** ([preprint](https://doi.org/10.5281/zenodo.21715908)): peer-reviewed (JOSS, N=173) vs.
  unreviewed (Europe PMC, N=257) research software — packaging 95% vs. 42%, install-decay 37% vs. 61%
  (both significant), revival ~92% on both arms. Methods in `paper/CROSSDOMAIN_METHODS.md`; per-repo
  tables S1–S4 in `paper/supplement/`.
- **40+ revivals across a dozen fields** (biology + materials, chemistry, hydrology, astronomy, plasma
  physics, …) — the agent generalizes past biology.
- **Roadmap** (`docs/roadmap.md`) — a tiered community vision.

### Changed
- Hardened the independent verifier (`interpret_smoke`): scientific-notation parsing + explicit
  higher/lower-is-better vocabularies; returns *inconclusive* rather than a false pass on an
  un-nameable metric (with unit tests).
- Repo tidy: README reworked into four acts; paper methods + analysis grouped under `paper/`; the
  composed pipeline brick moved to `pipelines/`; superseded benchmark intermediates pruned.

### Fixed
- Public tools' contracts reference their GHCR image (not a local build tag), so `lazarus pull` → run
  works for anyone — verified anonymously pullable end-to-end.

## [0.3.0] — 2026-07-18

### Added
- **`lazarus decay-check <url>`** — an agent-free "does this repo still install and run today?"
  check (the `naive_runs` decay signal), shipped in the package. Clone → install (conda/pip/R,
  no repair) → run a shipped example / README usage / import → reason-coded verdict. Two
  sandboxes: `host` (venv / temp R-lib — light) and `docker` (`continuumio/miniconda3` /
  `rocker/r-ver` — strict benchmark parity). Flags: `--sandbox`, `--fail-on-decay`, `--json`.
- **Decay-check GitHub Action** (`DoctorDean/lazarus/actions/decay-check@v0.3.0`) — run the
  check in any repo's CI on the repo's own runner minutes; a reproducibility canary
  (`fail-on-decay`) or a survey. Emits `naive-runs`/`stage`/`reason` outputs + a job summary.
- **Registry grew 6 → 13.** Promoted permissively-licensed benchmark revivals with verified
  contracts: DeepLatentMicrobiome, HiTEA, DnaFeaturesViewer, CoCoNet, EquiDock, EquiBind (all
  pullable from GHCR), plus Sequoya (rebuild-locally, image too large to publish).
- **Contributor on-ramp** — guided issue forms (request a repo · contribute a tool · report a
  failed revival · bug), a PR template, and a "good first issues" list in CONTRIBUTING.

### Fixed
- **Pulled contracts are now pull-and-run.** Public tools' contracts referenced the local build
  tag; they now point at their GHCR image, so `lazarus pull <tool>` → run works for anyone
  (verified end-to-end).

### Changed
- Docs site brought up to date with v0.2+ (benchmark headline, registry/pull, dashboard,
  component images, decay check).

## [0.2.0] — 2026-07-17

🏆 Winner, Build track — Claude Science hackathon.

### Added
- **Registry of revived tools** (`lazarus registry`, `lazarus pull`) — browse the catalog and
  pull any revived tool's contract (module + CLI + pinned container + smoke test). Resolves
  from a local `./registry` or the published index. Six tools to start: MaSIF-site, ScanNet,
  dMaSIF, fpocket, Basset, DiffDock.
- **Benchmark harness** (`benchmark/`) — Scout → resurrect → independent verify, with a
  reason-code taxonomy, harness-controlled reproduction tolerance, and a hard per-repo
  wall-clock cap. `report.py` summarises with **95% Wilson confidence intervals**.
- **Principled N=20 benchmark** (Bioinformatics, 2018–2021, seeded random sample):
  **85% of repos don't run on their own; Lazarus revived 100% of the dead** (17/17), 5
  reproduced the paper's metric. Full frame, seed, and per-repo outcomes are in `benchmark/`.
- **Public "try it" dashboard** (`demo/dashboard/`) — search a GitHub repo, watch a recorded
  resurrection replay, browse the registry. Starlette + SSE, no extra deps.
- **GHCR-published images** — MaSIF-site, ScanNet, fpocket, and DiffDock are now pullable from
  `ghcr.io/doctordean/lazarus-*`; see `docs/IMAGES.md`. dMaSIF and Basset stay rebuild-locally
  on licensing grounds.
- **Per-run cost capture** — resurrections now record `cost_usd` from the SDK when available.
- `CONTRIBUTING.md` and a `scripts/publish_images.sh` helper.

### Fixed
- **Wall-clock cap enforcement** — the benchmark watchdog fired a single, no-timeout
  `docker rm -f` over `ssh://` and swallowed failures, so one hung/failed kill let a capped
  run continue unbounded. Now a bounded, retried force-remove reliably tears the container down.

### Changed
- Registry `base_image` for the four permissive tools now points at their public GHCR images.
- Removed internal host coordinates from tracked files; dropped the video demo script.

## [0.1.1]

### Changed
- Removed the author email from the package metadata (privacy).

## [0.1.0] — 2026-07-10

First public release.

### Added
- **Commit-era dependency pinner** (`lazarus pin`) — resolves each dependency to the version
  live on PyPI at a repo's last-commit date. Pure Python; no repo execution.
- **Autonomous resurrection loop** (`lazarus resurrect`) — a build → run → read-traceback →
  repair loop in a disposable Docker sandbox (local, remote `ssh://`, or `--gpus`), isolated
  from host notes, that snapshots expensive successes.
- **The Scout** — `lazarus resurrect <github-url>` plans a revival from a bare URL: it reads the
  public repo + paper and writes its own goal and a *falsifiable* sanity check, then pauses for
  confirmation before spending compute.
- **Integration contracts** — every revival emits the same artifact: an importable module, a CLI,
  a pinned container, a smoke test, and an optional `REPRODUCE.md` benchmark certificate.
- **Lazarus Compose** (`lazarus run`) — wires revived contracts into a pipeline with a small YAML
  and runs them on the chosen host, passing artifacts between steps.
- **Five reference resurrections** in `examples/` — MaSIF-site, ScanNet, dMaSIF (GPU), fpocket
  (2010 C), and Basset (2016 Lua Torch7, genomics — revived from a URL, reproducing its paper).
- A zero-setup **Colab notebook**, a **MkDocs docs site**, and CI (test matrix + Trusted-Publishing
  release workflow).

[0.1.1]: https://github.com/DoctorDean/lazarus/releases/tag/v0.1.1
[0.1.0]: https://github.com/DoctorDean/lazarus/releases/tag/v0.1.0
