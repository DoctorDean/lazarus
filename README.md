# Lazarus

**Turn dead research code into a callable pipeline component.**

The method you need is often published, open, and completely unrunnable: the
repo is 3–5 years stale, wired to a stack that no longer resolves, and the real
capability is buried in shell scripts with no API. Getting it to run costs days
you don't have, so genuinely useful methods get abandoned.

Lazarus is an agent that clones such a repo, reads its paper for intent, and
runs a **build → execute → read-traceback → repair** loop in a sandbox. It
pins dependencies to the repo's commit era, resolves the external-binary chain,
locates the real capability, and emits a fixed **integration contract**:

- a pip-importable module,
- a CLI,
- a pinned container,
- and a smoke test that proves the method runs on a fresh input and passes a
  sanity check you define.

**Anchor case:** [MaSIF](https://github.com/LPDI-EPFL/masif) — a widely-cited
molecular-surface-fingerprint method, trapped behind Python 3.6, TensorFlow
1.x, a from-source PyMesh build, and an external-binary chain (MSMS, APBS,
PDB2PQR, reduce). Lazarus resurrects its interaction-site prediction and calls
it on a fresh structure.

## Status

Early. Built so far:

- **Commit-era pinner** (`lazarus pin`) — reconstructs the dependency universe
  as it was on a given date, using the PyPI release timeline. Deterministic,
  needs no execution of the target repo.

Roadmap: Docker-backed sandbox · traceback→repair loop · capability locator ·
contract emitter · MaSIF-site resurrection with a `4ZQK_A` ROC-AUC smoke test ·
a second dead repo to prove it generalizes.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Try the pinner

```bash
# What did MaSIF's stack actually look like on its last-commit era?
lazarus pin --date 2019-01-01 tensorflow numpy scipy biopython
# -> tensorflow==1.12.0  (matches MaSIF's Dockerfile, not its README)

# Or pin a whole requirements file:
lazarus pin --date 2019-01-01 --requirements requirements.txt
```

## Develop

```bash
.venv/bin/pytest -q
```

## License

MIT — see [LICENSE](LICENSE).
