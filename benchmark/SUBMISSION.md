# Submitting an agent

A submission is a **Docker image with a fixed command line**. The harness knows nothing
else about it — how you revive the repo is entirely your business.

> Status: the boundary is built and unit-tested (`benchmark/submission.py`). The public
> board, the queue and the held-out split are not (P3–P5 in
> [LEADERBOARD_SCOPE.md](LEADERBOARD_SCOPE.md)). You can develop against the dev tasks now.

## The contract

Your image is invoked as:

```bash
docker run --rm --network <policy> \
  -v <staged-task>:/task:ro -v <out>:/out \
  <your-image> \
    --repo-url  https://github.com/owner/repo \
    --commit    <40-char sha>              # or: --artifact-url <url> --artifact-sha256 <hash>
    --task      /task/task.yaml \
    --out       /out
```

You must:

1. Obtain the source at **exactly the given pin** — the commit, or the content-addressed
   artifact. Not `HEAD`. Tasks are pinned because upstream moves, sometimes because of
   fixes we ourselves contributed.
2. Get it running, by whatever means. Repair it, containerise it, patch it, rewrite the
   dependency set — this is the actual task.
3. Write the file named by `output_path` into `/out`, matching `output_schema`.
4. Exit. A non-zero exit is not fatal: **whatever you wrote is still graded**, because a
   crash after a correct write is not a wrong answer.

## What `/task` contains

`task.yaml` is a **redacted** copy of the task spec, plus `input/`. You get the capability
description, the input, the output path and schema, the metric, its direction and the
threshold — everything needed to know what is being asked and how well.

You do **not** get:

- `evaluation.labels` — the ground truth.
- `evaluation.reported` — for a `reproduce` task this *is* the answer, the number you are
  supposed to independently measure.

Grading happens after your container exits, outside it, against data it never saw. Staging
refuses to run if the answer key would end up inside `/task`.

## Output formats

| task | writes | schema |
|---|---|---|
| `scannet-ppi-4zqk`, `dmasif-ppi-4zqk` | `prediction.csv` | `resid,score` — one row per residue |
| `diffdock-dock-6moa`, `equibind-dock-6moa` | `prediction.sdf` | a docked pose |
| `pyamg-poisson-solve` | `solution.csv` | `index,value` — every index exactly once |
| `pysrurgs-symbolic-regression` | `prediction.csv` | `id,score` — one row per test id |
| `deepdta-davis-ci` | `result.txt` | `concordance_index=<value>` |

Rows are joined on their id column, never by position, so order does not matter — but every
required id must be present exactly once. Graders reject duplicate ids, missing ids,
non-finite values and unlabelled scalars rather than guessing.

## Caps, and which ones are real

Only some caps can be enforced against an opaque container, and it's worth being straight
about which:

| cap | enforced? | how |
|---|---|---|
| wall clock | **yes** | the harness kills the container at the task's `wall_clock_s` |
| memory, CPU | **yes** | container runtime limits |
| network | **yes** | see below |
| turns | no | internal to an agent; unobservable from outside |
| cost | no | self-reported metadata only |

Turns and cost appear in the task spec as guidance and are reported alongside results, but
they are **not rules and nothing is ranked on them**. Writing them down as enforced caps
would be a rule we cannot apply.

## Network

Reviving real software means downloading weights, packages and data, so the network is
open by default in spirit — but official runs go through a policy network that blocks
`github.com/DoctorDean/lazarus`, `ghcr.io/doctordean/*` and the `lazarus-bio` package.
Otherwise a submission could simply pull our published answer for a registry tool.

`benchmark/submission.py` takes the network name as a parameter and defaults to `none`.
Wiring the deny-list proxy is P4 infrastructure and is not built yet; until it is, treat
"don't fetch the Lazarus registry" as a rule you're on your honour to follow, and expect it
to become enforced.

## Scoring

Revival rate — the fraction of tasks whose evaluator passes — is the ranking. Reproduction
rate, cost and wall clock are reported but not ranked. Row zero of every board is the
agent-free baseline (`benchmark/baseline.py`): a submission that cannot beat "does the repo
just run today" has demonstrated nothing.

Runs that cannot be graded at all (no output, unparseable output, evaluator error) are
reported separately and kept **out of the rate denominator**, so a harness bug cannot
deflate your score.

## Developing locally

```python
import sys; sys.path.insert(0, "benchmark")
from lazarus.sandbox import DockerClient, find_docker
from submission import Submission, run_and_grade
from task import load_task

task = load_task("benchmark/tasks/dev/scannet-ppi-4zqk/task.yaml")
run, score = run_and_grade(
    Submission(name="mine", image="ghcr.io/me/agent:1"), task, "/tmp/work",
    client=DockerClient(binary=find_docker()), network="bridge")
print(run.ok, score.passed, score.measured)
```

The dev tasks are deliberately contaminated — every one is a tool already in the Lazarus
registry with a published contract. They exist so you can develop against a known answer.
The held-out split will not be like this.
