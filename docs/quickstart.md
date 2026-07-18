# Quickstart

## Install

=== "Just the tooling"

    ```bash
    pip install lazarus-bio
    ```

    Gives you the commit-era dependency pinner and the contract/compose tooling. Pure Python,
    no Docker.

=== "Full agent (revive + Scout)"

    ```bash
    pip install "lazarus-bio[agent]"   # needs Python >= 3.10 + Docker
    ```

    Adds the autonomous resurrection loop and the URL Scout, which drive Claude via the
    [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python).

Prefer zero install? **[Open the notebook in Colab](https://colab.research.google.com/github/DoctorDean/lazarus/blob/main/notebooks/Lazarus_Democratizing_Dead_SOTA.ipynb)** — a 2-minute tour with no Docker or GPU.

## Start here: pull a revived tool from the registry

If someone already revived the tool you need, don't re-revive it — pull its contract (an
importable module, a CLI, a pinned container, and the smoke test that proves it runs):

```bash
lazarus registry                          # browse what's already revived
lazarus pull scannet_ppi_binding_sites    # fetch its contract bundle
```

The four permissively-licensed tools also ship a public image on GHCR — e.g.
`docker pull ghcr.io/doctordean/lazarus-fpocket:working` (see [Component images](IMAGES.md)).
Need something that isn't in the registry yet? Revive it yourself below.

## Is it actually dead? — `decay-check`

Before reviving, confirm the repo really doesn't run today (agent-free, no API key):

```bash
lazarus decay-check https://github.com/owner/repo     # RUNS / DECAYED + a reason code
```

Add `--sandbox docker` for a fresh-container check, or `--fail-on-decay` to gate CI. It's also
a **[GitHub Action](decay-check.md)** — a reproducibility canary for your own repo.

## 1. Pin dependencies to a repo's commit era

The single biggest reason old code "won't install" is that `pip` gives you *today's* versions.
Lazarus reconstructs the dependency universe as it was on the repo's last commit — no repo
execution required.

```bash
lazarus pin --date 2019-01-01 tensorflow numpy scipy
#   tensorflow==1.12.0   (matches MaSIF's real Dockerfile, not its README's 1.9)
```

## 2. Resurrect a repo — from just a URL

The Scout reads the repo + paper, writes the goal and a falsifiable sanity check, picks a base
image, and pauses for your OK before spending compute:

```bash
lazarus resurrect https://github.com/jertubiana/ScanNet
```

Or drive it by hand with an explicit image + goal (both override the Scout):

```bash
lazarus resurrect --image pablogainza/masif:latest --workdir /masif \
  --goal-file examples/masif_site_goal.txt --keep
```

!!! note "Where it executes"
    Lazarus runs on your machine; *where it executes* is one flag. Point `--docker-host` at a
    local daemon, a remote x86 box (`ssh://you@host`), or a cloud/GPU rental — for methods whose
    binaries need hardware a laptop can't emulate.

## 3. Compose revived bricks into a pipeline

```bash
lazarus run examples/pipelines/binder_triage.yaml \
  --input structure=4ZQK.pdb \
  --registry examples --registry components \
  --docker-host ssh://you@your-x86-gpu-box
```

See [Compose & reproduce](compose.md) for what the pipeline concluded on PD-L1.

## Auth

Log in the `claude` CLI (subscription) or drop `ANTHROPIC_API_KEY=...` in a gitignored `.env` —
`lazarus` loads it without ever putting the secret on the command line.
