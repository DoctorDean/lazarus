# Handoff — benchmark / leaderboard work

State as of **2026-09-15**, branch `next` (161 hermetic tests green in ~0.7 s, plus 2 opt-in
Docker tests). Read this with [LEADERBOARD_SCOPE.md](LEADERBOARD_SCOPE.md), which holds the
full design and the phase table.

> **P2 IS CLOSED (2026-09-15).** The reference submission ran end-to-end through the real
> contract and **PASSED**: `pyamg-poisson-solve`, `relative_residual=4.93e-16` against a
> `≤1e-8` bar, 21 turns, 7.9 min, on the **Mac (arm64)** — no Bertha involved. All six
> integration points are proven. **The next action is P3**, the held-out test set.

---

## 1. The one-paragraph version

Lazarus **v0.5.0 is released** (PyPI, tagged on merge commit `73bbfba`) — its headline is the
flagship pipeline where four resurrected tools converge on a real drug pocket in BRD2. All work
since then builds a **public benchmark** ("SWE-bench for resurrecting dead research software")
so *other people's* agents can be scored. The grading layer, a 7-task dev split and the
submission boundary are built and tested. The held-out test set — the thing that produces a
publishable number — does not exist yet.

## 2. The engine is untouched — keep it that way

`src/` and `pyproject.toml` are **byte-identical to the `v0.5.0` tag**. Verify before assuming:

```bash
git diff --stat v0.5.0..next -- src/ pyproject.toml     # must be empty
```

The wheel ships only `lazarus/`; nothing under `benchmark/` is packaged. Existing users of
`pip install lazarus-bio` are unaffected by any of this work.

**This is a constraint, not an accident.** The benchmark must not grow features into the
shipped package for its own convenience. It has already been tempting twice — see §6.

## 3. What is built

| Phase | Where | State |
|---|---|---|
| **P0** grading layer | `task.py`, `evaluators.py`, `score.py`, `run.py:apply_task_score` | done |
| **P1** dev split | `tasks/dev/*`, `mine_tasks.py`, `tasks/pins.json` | done (7 tasks, 4 domains) |
| **P2** submission boundary | `submission.py`, `SUBMISSION.md`, `reference/`, `run_reference.py` | **done** — proven end-to-end against a real agent (§4) |
| **P3** held-out test set | — | not started (the expensive phase) — **now the next action** |
| **P4** scoring, board, proxy | — | not started |
| **P5** baseline + launch | — | not started |

The core idea of P0: **the harness owns the definition of "solved"**, not the agent. Previously
the Scout wrote its own sanity metric and `verify_smoke` re-ran the agent's own smoke command —
fine for cataloguing revivals, useless for ranking competitors.

Seven dev tasks, all `predict` except one:

```
deepdta-davis-ci              reproduce  concordance_index within ±3% of 0.878
diffdock-dock-6moa            predict    centroid_distance_A ≤ 2.0
dmasif-ppi-4zqk               predict    auroc ≥ 0.7
equibind-dock-6moa            predict    centroid_distance_A ≤ 2.0
pyamg-poisson-solve           predict    relative_residual ≤ 1e-08   (self-verifying)
pysrurgs-symbolic-regression  predict    r_squared ≥ 0.9
scannet-ppi-4zqk              predict    auroc ≥ 0.7
```

Every one was validated by grading real output through the task layer and reproducing the
number the original revival recorded (ScanNet 0.9233, dMaSIF 0.8390, DiffDock 0.223 Å,
EquiBind 0.838 Å). That agreement is the evidence the grading path is sound.

## 4. P2 IS PROVEN END-TO-END — the next action is P3

**The reference submission completed a real task through the real contract and passed.**
2026-09-15, on the Mac (arm64), no Bertha:

```
task      pyamg-poisson-solve  (predict, numerical linear algebra)
criterion relative_residual ≤ 1e-08
PASS      relative_residual = 4.932671474961411e-16     # 21 turns, 7.9 min
```

The agent built pyamg **from source at the pinned commit** (meson-python, numpy 2.5.3, scipy
1.18.1), snapshotted `lazarus/pyamg:solver-ready`, emitted contract `pyamg_spd_solve`, and
wrote a conforming `index,value` CSV — 625 rows, indices 0..624 each exactly once. The
residual is ~8 orders inside the bar and beats the 1.4e-15 direct dense solve the task notes
cite as reference. Record: `/tmp/lazarus-bench3/pyamg-poisson-solve/record.json`.

Note what the harness did *not* do: it ignored the agent's self-reported residual and
recomputed the score from `A.mtx`/`b.txt`. That is P0's whole point, exercised for real.

The attempt on 2026-09-08 found **six** bugs, four of which a mocked runner cannot see; the
first real run on 2026-09-15 found a **seventh** (§6.10, the root permission gate). All are
fixed, and **all six integration points are now proven**:

| # | Integration point | State |
|---|---|---|
| 1 | Docker socket plumbing into the submission container | ✅ preflight passes with it, fails in seconds without |
| 2 | `claude` CLI present and working in the image | ✅ 2.1.259; `find_claude_cli()` resolves it |
| 3 | `ANTHROPIC_API_KEY` reaching the resurrection loop | ✅ arrives byte-identical (host/container sha256 match), SDK authenticates with it |
| 4 | `bake_input_image()` producing a usable derived image | ✅ input byte-identical under root + `:ro`, no builder |
| 5 | the agent writing a *conforming* CSV | ✅ `index,value`, 625 rows, indices 0..624 each once, from a real agent |
| 6 | copy-out of `/lazarus_result/<output_path>` | ✅ lands on host `/out`, from a bash-less image |

Grading a conforming file reproduces **0.9233** exactly, and the whole boundary — staging,
argv, mounts, exit code, `score.grade` — is driven by a stub submission in
`tests/test_reference_integration.py`, which also asserts *from inside the container* that
`labels`, `reported` and `0.9233` never crossed. The staged `/task` mount was re-checked after
the live run: it holds only `task.yaml` (the redacted `public_view`) and `input/`, with zero
occurrences of `reported` or `labels`.

```bash
# The proven command — arm64-native, self-verifying, ~8 min. Needs a live key in .env:
export PATH="$HOME/.orbstack/bin:$PATH"
.venv/bin/python benchmark/run_reference.py \
    --task benchmark/tasks/dev/pyamg-poisson-solve/task.yaml \
    --image lazarus-submission:local --work /tmp/lazarus-bench

# Then this one, on Bertha, once it is back — x86-only image, so it cannot run on the Mac:
python benchmark/run_reference.py --task benchmark/tasks/dev/scannet-ppi-4zqk/task.yaml \
    --image lazarus-submission:0.5 --work /tmp/lazarus-bench
```

Run it **where the compute is**: over ~90 turns of `docker exec`, a tunnelled daemon is
materially slower than a local one, which is why the harness and `src/` are rsynced to
`~/lzb` on Bertha rather than driven over `DOCKER_HOST=ssh://`.

**A revoked key cost a run here — check it first (§10).** The July hackathon key in `.env` had
been revoked, returning `401 authentication_error`; that is *not* exhausted credit, which
returns `400 credit balance is too low`. Dean replaced it on 2026-09-15 and `GET /v1/models`
now returns 200. Discovering this through the runner took 3 minutes of retries; the §10
precheck takes one second.

**Bertha was NOT required to close points 3 and 5, and is not required for P3 either.** It is
still offline (2026-09-15: 11 days,
`LastSeen 2026-09-03T23:58:32Z`, no handshake, relay only; node key valid to 2027-01-04, so
this is the machine, not re-auth). Bertha looked like the blocker only because the chosen task
was **ScanNet** — an x86 TF 1.14 image that traps under qemu. Points 3 and 5 were
architecture-independent all along, and **`pyamg-poisson-solve`** closed them on the Mac: pure
Python/numpy/scipy, arm64-native, self-verifying. `lazarus-submission:local` is built here for
linux/arm64 with `docker-cli`, claude CLI 2.1.263 and lazarus 0.5.0 in it.
**Generalise this when picking P3 tasks:** an arm64-friendly, self-verifying task can be
developed and graded entirely on the Mac, so prefer those and keep the x86-only ones for
whenever Bertha returns. A benchmark that can only be exercised on one offline box is a
benchmark that stops being exercised.

Bertha is still wanted eventually, for the x86-only revivals (ScanNet, dMaSIF, DiffDock).
In place there: `~/lzb/{benchmark,src}`, a venv with `pyyaml numpy packaging`, and
`lazarus-submission:0.5` built; missing only `~/lzb/.env` (mode 600).

**Why this went before P3, and why that ordering was right:** P3 is weeks of per-task
ground-truth work that cannot be automated. Building 50 tasks against an unproven runner is how
you find the chain is broken after the costly part is sunk. **Seven** bugs in a fully
unit-tested phase — the seventh fatal within 2.4 seconds — is the evidence for that ordering,
not a hypothetical. The boundary is now proven, so P3's cost is safe to incur.

## 5. Settled decisions — do not re-litigate

- **Test split is `predict`-only.** A `reproduce` target is printed in the paper, so it can be
  looked up rather than computed. `reproduce` is dev-only; it exists for exactly one task.
- **Scope is cross-domain**, not comp-bio only. Every task carries a `domain` field.
- **Dev target cut from ~20 to ~9**, and it is a *coverage* target, not a count. Rationale in
  scope §10: nothing is computed from the dev split, so N there buys nothing. N matters for the
  **test** split, where a 90% rate at N=20 has a ±27pp Wilson CI vs ±12pp at N=100.
- **Ranking is revival rate.** Cost and wall clock are reported, never ranked.
- **Ungradable ≠ failed.** Runs the harness cannot grade stay out of the rate denominator, so a
  harness bug cannot deflate an agent's score.
- **Submissions are run by the submitter** (Dean, 2026-09-08). He will not run them himself.
  P4 therefore needs no run-queue and no per-submission compute budget; it needs a
  *results-submission* path plus whatever makes a self-run trustworthy — logged runs, the
  deny-list proxy, spot re-runs. This is also why the socket and credential grants in
  `build_argv` are named and default-off: they are reference-only, and a submitter brings
  their own key on their own hardware.

## 6. Findings that shaped the design — know these before changing anything

**6.1 The recorded results cannot supply ground truth.** Of the 33 non-null
`reproduced_reported` values in `results*.json`, **20 are not paper numbers** — 14 byte-identical
to the run's own `sanity_threshold`, the rest round self-consistency bars (`pearson_r=1`,
`max_abs_diff=0`). They are the agent's bar for itself in a field named as if it came from the
literature. Lifting them would rebuild the exact self-grading problem P0 removes. Hence
`mine_tasks.py` classifies candidates (`check-paper` 14 / `agent-bar` 19 / `no-target` 34) and
writes a **review manifest, never a task**. Scope §2.4.

**6.2 Self-verifying tasks are the best kind.** Graded by recomputation from the input — a
residual, an energy, a constraint that holds or doesn't. No answer key exists, so they cannot
be leaked or contaminated, and anyone can audit the score. `pyamg-poisson-solve` is the model.
**Prefer these for the test split.** Ranking of patterns in scope §9.

**6.3 The schema assumed git.** fpocket is a 2010 SourceForge tarball; Basset came from a 2016
Docker image. Requiring a commit SHA would bias the benchmark toward modern, well-packaged code
— inverting the v0.4 finding. Fixed with a polymorphic pin (`commit` XOR `artifact_url` +
`artifact_sha256`). **No task uses the artifact path yet**: SourceForge blocks automated
downloads (HTML interstitial one way, 2 bytes the other), so fpocket's hash is unobtainable.
Do not invent one.

**6.4 Staging nearly handed over the answer.** `labels/` sits next to `input/` in a task dir,
and for a `reproduce` task `evaluation.reported` **is** the answer. `Task.public_view()` redacts
both; `stage_task()` byte-compares staged files against the label file and refuses to run on a
leak. A staging bug would invalidate every later score *while looking like an excellent
submission*.

**6.5 Turns and cost are not enforceable.** Against an opaque container only wall clock, memory,
CPU and network can be enforced. Turns and cost are internal to an agent. They are self-reported
metadata and **nothing may be ranked on them**.

**6.6 The wrapper's container boundary.** The revival happens in a *different* container from
the submission, so `/out` and `/task` do not exist where the agent works, and its tools
deliberately cannot write the host (`emit_contract` writes a contract bundle, nothing else). The
wrapper therefore bakes input into a derived image and copies the result back out. Both
wrapper-side — **this is the seam that keeps the benchmark out of `src/`.** If a future fix
tempts you toward teaching the Scout or the contract emitter about output schemas, that is a
product decision; raise it, don't do it quietly.

**6.7 `notes` leaked calibration, and no guard objected.** `Task.public_view()` stripped
`evaluation.labels` and `evaluation.reported`, but passed `notes` through — and this very
task's notes end "Lazarus's own revival measured 0.9233 on this input." That is not the
answer key, so neither `validate()` nor `stage_task()`'s byte-comparison against the label
file complained, yet it tells an agent the score a working revival achieves, i.e. when to
stop trying. `notes` is now stripped; `capability` is the field that describes a task
publicly. **The lesson generalises: the leak checks test for the answer, not for
information about the answer.** Any new field on `Task` needs that second question asked.

**6.8 Four of the six bugs were invisible to a mocked runner.** P2 was fully unit-tested
and broken in six places, because the fakes agreed with the code about the environment.
Specifically: `/task` is mounted `:ro`, so a Dockerfile could not be written beside the
input (EROFS as *root* — mode bits would not have caught it); Debian trixie ships
`docker.io` as the **daemon** with the client split into `docker-cli`, a Recommends that
`--no-install-recommends` drops, so the image built green with no `docker` binary at all;
`build_argv` could pass the submission neither a credential nor a socket, making the
reference unrunnable *through* the harness; and Debian's `docker-cli` carries no buildx
plugin, so `docker build` inside the submission fell back to the deprecated legacy builder,
which cannot export a cross-platform image (`failed to export image: NotFound: content
digest ...`). `tests/test_reference_integration.py` now covers this ground against a real
daemon, opt-in via `LAZARUS_DOCKER_TESTS=1` so the hermetic suite stays sub-second.

**6.9 Prefer the engine's primitives over a second mechanism.** The buildx failure was
fixed not by adding a builder to the image but by deleting the build: `bake_input_image()`
now does copy-and-commit through `lazarus.sandbox.Sandbox`, the same primitive the engine
already uses to bank a successful build. No builder, no context, no Dockerfile, and one
fewer thing a third-party wrapper must get right. Relatedly, two wrapper calls passed
*strings* to `Sandbox.exec`, which runs them under `bash -lc` — a revival image is not
obliged to have bash, and the copy-out would have reported "no result to collect" for a
file that existed. List form now. Note `Sandbox.write_file` still requires bash; that is
engine code and stays untouched (§2).

**6.10 The CLI refuses `--dangerously-skip-permissions` as root** (2026-09-15, bug #7).
`lazarus.scout` and `lazarus.resurrect` both set `permission_mode="bypassPermissions"`, so the
SDK passes that flag; the reference image has no `USER` directive, so it runs as root; and the
CLI aborts with *"cannot be used with root/sudo privileges for security reasons"*. The Scout
died **2.4 seconds** into the first real end-to-end run. Fixed wrapper-side with
`ENV IS_SANDBOX=1` in `benchmark/reference/Dockerfile` — the documented escape for an
already-isolated container, and here the container *is* the isolation boundary. Verified by
A/B probe: without it, the refusal; with it, the CLI reaches the API and returns a clean 401 on
a deliberately bogus key. The rejected alternative was a non-root user, which would have to
match the host's docker gid to keep the mounted socket usable — not portable between hosts, and
this image is meant to be copied by third parties.
**Two lessons.** First, the fix had to stay out of `src/` (§2): the *cause* is in engine code,
the *fix* belongs in the wrapper. Second, and more useful: **this bug is not
architecture-specific, so the long-awaited Bertha run would have died in exactly the same way.**
Waiting for the x86 box would have bought nothing. Points 3 and 5 never needed it — see §4.

## 7. Traps

- **Never hand-type a commit SHA.** One plausible-but-fabricated EquiBind SHA got written during
  P1; a format regex accepts it. `tasks/pins.json` is the record of what was really resolved
  upstream, and a test asserts every task SHA matches it.
- **Check a new test actually fails without the fix.** Two tests in this work passed either way
  on first writing (the runner regressions; the goal-leak guard) and had to be reframed.
- **Calibrate a threshold against real data.** `pysrurgs` at 0.90 looked rigorous but a linear
  fit had to be measured (0.107) to know it discriminates. DeepDTA's default ±15% band would
  have admitted the paper's own weaker ablations.
- **`_force_remove` defaults to a 120 s budget.** Reusing it naively made the P2 suite take
  120 s; `run_submission` passes `kill_budget_s=30`.
- **GitHub API is 60/hr anonymous.** All 67 repos are already pinned in `tasks/pins.json`, so
  no lookups are needed. Optional `GITHUB_TOKEN` in `.env` (no scopes — every repo read is
  public) lifts it to 5000/hr, which P3 will want.

## 8. Open decisions for Dean

1. **Test set size** — 50 tasks ≈ $60–80 and ±17pp CI; 100 ≈ ±12pp.
2. **Where test ground truth comes from** — the real bottleneck. Self-verifying targets are
   preferred but each needs domain knowledge to define. Which fields, and any preferred sources?

*Who runs official submissions* was the third question here and is now settled — see §5.

## 9. Also outstanding, outside the benchmark

The **reproducibility observatory** — the other Tier-1 roadmap track (continuous `decay-check`
over a large corpus plus a public dashboard) — has not been touched. It may matter more than the
leaderboard for actual adoption.

## 10. Resume commands

```bash
git diff --stat v0.5.0..next -- src/ pyproject.toml        # expect empty (§2)
.venv/bin/python -m pytest -q                              # expect 161 passed, 2 skipped
LAZARUS_DOCKER_TESTS=1 .venv/bin/python -m pytest -q \
    tests/test_reference_integration.py                    # expect 2 passed; needs Docker
.venv/bin/python benchmark/task.py --root benchmark/tasks  # list + validate the dev split
tailscale status | grep bertha                             # is the box back yet?
ssh dean@100.80.108.2 nvidia-smi                           # ...and does it have its GPU
```

Check the credential before spending anything — a revoked key costs 3 minutes of retries to
discover through the runner, and one second to find here:

```bash
.venv/bin/python -c 'import sys,os,urllib.request,urllib.error; sys.path.insert(0,"src");
from lazarus.cli import load_dotenv; load_dotenv(".env");
req=urllib.request.Request("https://api.anthropic.com/v1/models",
  headers={"x-api-key":os.environ["ANTHROPIC_API_KEY"],"anthropic-version":"2023-06-01"});
print("key OK" if urllib.request.urlopen(req,timeout=25).status==200 else "?")'
```

If `tailscale status` reports `Tailscale is stopped`, that is the **Mac's** client being down,
not Bertha — reconnect with `tailscale up --accept-routes` (the flag must be repeated or
`up` refuses) before concluding anything about the box.
