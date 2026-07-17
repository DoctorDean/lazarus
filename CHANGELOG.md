# Changelog

All notable changes to Lazarus (`lazarus-bio`) are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/).

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
