# Changelog

All notable changes to Lazarus (`lazarus-bio`) are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/).

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

[0.1.0]: https://github.com/DoctorDean/lazarus/releases/tag/v0.1.0
