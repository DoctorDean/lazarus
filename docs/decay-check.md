# Decay check

**Does this repo still install and run today?** The agent-free reproducibility signal —
the same `naive_runs` check that found *85% of a random sample of recent Bioinformatics
tools don't run on their own*. Available as a CLI and a GitHub Action. No agent, no API key.

## CLI

```bash
pip install lazarus-bio
lazarus decay-check https://github.com/owner/repo
```

It shallow-clones the repo, installs from its own files (conda / pip / R — first manifest
wins, **no repair**), runs a shipped example (or the README's usage block, or a bare import),
and prints a verdict with a reason code:

```
https://github.com/owner/repo
  DECAYED — does not run on its own today
  stage/reason: install/pip_install_failed  (python, host, 42s)
  → Lazarus can revive it: https://doctordean.github.io/lazarus/
```

Options: `--sandbox host|docker` · `--fail-on-decay` (non-zero exit for CI) · `--json` ·
`--timeout <s>` · `--docker-host ssh://…` (docker sandbox).

**Two sandboxes:**

- **`host`** (default) — runs on the current machine; Python installs into a throwaway venv,
  R into a temp library. Light, no images. A fresh CI runner *is* the clean environment.
- **`docker`** — runs in a fresh `continuumio/miniconda3` / `rocker/r-ver` container. Strict
  parity with the published benchmark. Verdicts are less sensitive to the host toolchain.

## GitHub Action

### Reproducibility canary — watch your own repo
```yaml
# .github/workflows/decay-check.yml
name: decay-check
on:
  schedule: [{ cron: "0 6 1 * *" }]   # monthly
  workflow_dispatch:
jobs:
  decay:
    runs-on: ubuntu-latest
    steps:
      - uses: DoctorDean/lazarus/actions/decay-check@v0.3.0
        with:
          fail-on-decay: true          # a red build = "your code no longer runs"
```

### Check any repo
```yaml
      - uses: DoctorDean/lazarus/actions/decay-check@v0.3.0
        with:
          repo: https://github.com/owner/repo
          fail-on-decay: false         # informational; never fails the job
```

### Use the outputs
```yaml
      - id: decay
        uses: DoctorDean/lazarus/actions/decay-check@v0.3.0
      - run: echo "runs=${{ steps.decay.outputs.naive-runs }} reason=${{ steps.decay.outputs.reason }}"
```

**Inputs:** `repo` (default: this repo) · `sandbox` (`host`\|`docker`) · `fail-on-decay` ·
`timeout` · `python-version` (default `3.11`) · `version` (pip spec).
**Outputs:** `naive-runs` · `stage` · `reason`. Every run writes a job summary; a decayed
result links back here.

## Reason codes

| naive_runs | stage / reason |
|---|---|
| ✅ true | `example/ran_ok`, `example/imports_only` |
| ❌ false | `install/{pip_requirements_failed, pip_install_failed, conda_env_failed, R_install_failed, no_install_manifest}`, `example/{example_exit_N, no_example_found}`, `install/{needs_conda, needs_r, venv_failed}`, `timeout/hard_cap` |

## What it does and doesn't mean

A **pass** means "installs and a shipped example runs to exit 0" — *not* that the science is
correct. A **fail** in `host` mode reflects the runner's toolchain (pin `python-version`, or use
`sandbox: docker` for host-independent verdicts). It only tries the repo's own artefacts — no
repair — which is exactly what makes it a fair measure of decay, and the counterfactual Lazarus
is measured against.
