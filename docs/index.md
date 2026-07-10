<p align="center">
  <img src="https://raw.githubusercontent.com/DoctorDean/lazarus/main/lazarus.png" width="380" alt="Lazarus" />
</p>

# Lazarus

*Turn dead research code into a callable pipeline component — and give the revival back.*

[:material-rocket-launch: Quickstart](quickstart.md){ .md-button .md-button--primary }
[:material-notebook: Open in Colab](https://colab.research.google.com/github/DoctorDean/lazarus/blob/main/notebooks/Lazarus_Democratizing_Dead_SOTA.ipynb){ .md-button }
[:material-github: GitHub](https://github.com/DoctorDean/lazarus){ .md-button }

---

## The wall

Computational science has a reproducibility problem. A huge fraction of published methods
are **open, cited, and unrunnable** within a few years: the repo is stale, wired to a stack
that no longer resolves, and the real capability is buried in scripts with no API. The exact
method you need *exists* — but getting it to run costs days you don't have, so it gets abandoned.

## What Lazarus does

Lazarus is an agent that **revives** dead research code, lets you **compose** the revivals into
pipelines, and **gives the fixes back** to the community.

- **Revive** — point it at a **bare GitHub URL**. A web-enabled Scout reads the repo + paper and
  writes its own goal and a *falsifiable* sanity check; the agent then runs a
  build → run → read-traceback → repair loop in a sandbox and emits a fixed **integration
  contract** (importable module, CLI, pinned container, smoke test).
- **Compose** — every revival emits the *same* contract, so a revived tool is a composable
  **brick**. Wire bricks from any domain/language/era into a pipeline with a little YAML.
- **Give back** — the fixes (rotted URLs, broken paths, a 15-year-old undefined-behaviour bug)
  become maintainer-ready **pull requests** with CI, so the method can't silently rot again.

## Five dead repos, resurrected autonomously

| Repo | Era / stack | Result |
|---|---|---|
| **MaSIF-site** | Py3.6 · TF 1.12 · MSMS/APBS | interaction sites, ROC-AUC 0.9137 |
| **ScanNet** | Py3.6 · TF 1.14 · Keras | binding sites, ROC-AUC 0.9233 |
| **dMaSIF** | torch cu111 · PyKeOps · **GPU** | binding sites, ROC-AUC 0.8390 |
| **fpocket** | **2010 C** on modern GCC | 3 druggable pockets |
| **Basset** | **2016 Lua Torch7** · genomics | from a URL → reproduced the paper, AUROC 0.894 vs 0.895 |

Each was revived from its own dead environment using only general heuristics — no repo-specific
notes — and emits a package that passes its own smoke test standalone. The hard-won details are in
[the hard problems it solved](CHALLENGES.md).

## Install

```bash
pip install lazarus-bio
```

The base install (dependency pinner, contract/compose tooling) needs nothing but Python ≥ 3.9.
The autonomous loop + Scout need the agent extra and Docker:

```bash
pip install "lazarus-bio[agent]"
```

Next: the [Quickstart](quickstart.md), or [how it works](how-it-works.md).
