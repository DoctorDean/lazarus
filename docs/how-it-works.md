# How it works

Lazarus is a Python package on the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)
with a Docker-backed sandbox. A resurrection runs through six organs.

| Organ | Role |
|---|---|
| **Scout** | Reads a bare repo URL + its paper (web-enabled, but blind to your notes) and drafts the plan: capability, base image, and a *falsifiable* sanity check — so a revival starts from a link, not a hand-written goal. |
| **Sandbox** | Disposable container (CPU or GPU); every expensive success is snapshotted so a later failure never re-pays the build. |
| **Commit-era pinner** | Reconstructs the dependency universe as it was on the repo's last commit — the reasoning that beat the cu111/KeOps/`cppyy` tangle. |
| **Repair loop** | build → run → read traceback → patch → retry, bounded, isolated to the container. |
| **Capability locator** | Finds where "input → the famous output" happens and carves the minimal path to it. |
| **Contract emitter** | Module + CLI + pinned container + smoke test — CPU or GPU, verified callable on its own. |

## The integration contract

Every revival emits the **same** artifact — that uniformity is what makes a revived tool a
composable brick. A contract (`lazarus.yaml`) declares a pinned base image, typed inputs/outputs,
a containerised entrypoint using `$INPUT` / `$OUTDIR`, a **smoke test** (a metric + threshold you
define), and — when the method reproduces a published number — a **benchmark** that emits a
`REPRODUCE.md` certificate.

```python
from lazarus.contract import Contract

c = Contract.from_yaml(open("examples/basset_predict_contract/lazarus.yaml").read())
print(c.name, c.base_image, c.smoke.metric, c.benchmark.measured)
# basset_predict lazarus/basset:site-ready mean AUROC... 0.8944
```

## The Scout: reviving from a URL

The Scout is the one step allowed to see the outside world (it reads the public repo + paper via
web tools) — but it is explicitly cut off from your local notes, memory, and project settings, so
the downstream resurrection stays honest: it's solved from public information, exactly what a
newcomer has. It emits a validated plan whose sanity check must be *falsifiable* (a metric +
threshold, or an explicitly checkable qualitative assertion) — a revival that can't fail proves
nothing.

Pointed at Basset (`github.com/davek44/Basset`) with no hints, the Scout picked the
README-endorsed base image and wrote a benchmark-grade sanity check; the agent then reproduced the
paper — and in doing so caught a *silent* soft-masking bug that a naive run would have shipped. The
full gauntlet across all five repos is in [the hard problems it solved](CHALLENGES.md).

## Runs on a laptop, executes anywhere

Lazarus drives from your machine; *where it executes* is pluggable via one flag — a local
container, a remote x86 box, a cloud VM, or a GPU rental. The agent's tools and the emitted
`predict.py` both run against whatever `--docker-host` / `DOCKER_HOST` points at, so the whole
chain is host-agnostic.
