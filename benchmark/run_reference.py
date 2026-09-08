#!/usr/bin/env python3
"""Drive one task through the submission boundary with the reference submission.

``run.py`` runs Lazarus by importing it. This runs Lazarus as an *opaque image* through
exactly the contract in ``SUBMISSION.md`` — the path a third-party agent will take — so
the plumbing between harness and submission is exercised rather than assumed.

    python benchmark/run_reference.py \\
        --task benchmark/tasks/dev/scannet-ppi-4zqk/task.yaml \\
        --image lazarus-submission:0.5 --work /tmp/lzb

Run it **where the compute is.** The reference submission drives containers to do its
revival, so it needs a Docker daemon and an ``ANTHROPIC_API_KEY``; over ~90 turns of
``docker exec`` a tunnelled daemon is materially slower than a local one.

Two privileges are handed to the container here that a third-party submission must not
get: the host Docker socket, and the API key. Both are explicit flags on
``run_submission`` for that reason — see :func:`submission.build_argv`. An untrusted image
gets a disposable remote daemon and the submitter's own credentials.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import score as _score                                   # noqa: E402
from submission import Submission, run_submission        # noqa: E402
from task import load_task                               # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--task", required=True)
    ap.add_argument("--image", default="lazarus-submission:0.5")
    ap.add_argument("--work", default="/tmp/lazarus-bench")
    ap.add_argument("--network", default="bridge",
                    help="reviving real software needs to download things")
    ap.add_argument("--timeout-s", type=int, default=None,
                    help="override the task's wall_clock_s cap")
    ap.add_argument("--env-file", default=str(ROOT.parent / ".env"))
    ap.add_argument("--name", default="lazarus-reference")
    args = ap.parse_args(argv)

    sys.path.insert(0, str(ROOT.parent / "src"))
    from lazarus.cli import load_dotenv
    from lazarus.sandbox import DockerClient, find_docker

    load_dotenv(args.env_file)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(f"no ANTHROPIC_API_KEY (looked in {args.env_file}) — the submission "
              f"cannot run its agent", file=sys.stderr)
        return 2

    task = load_task(args.task)
    client = DockerClient(binary=find_docker())
    if not client.available():
        print("no Docker daemon answering", file=sys.stderr)
        return 2

    work = Path(args.work) / task.id
    work.mkdir(parents=True, exist_ok=True)
    print(f"task     {task.id}  ({task.kind}, {task.domain})")
    print(f"repo     {task.repo_url} @ {task.commit[:12] or task.artifact_url}")
    print(f"criterion {task.evaluation.metric} "
          f"{'≥' if task.evaluation.direction == 'higher' else '≤'} "
          f"{task.evaluation.threshold}")
    print(f"cap      {args.timeout_s or task.caps.wall_clock_s}s wall clock\n")

    run = run_submission(
        Submission(name=args.name, image=args.image), task, work, client=client,
        network=args.network, timeout_s=args.timeout_s,
        env_passthrough=("ANTHROPIC_API_KEY",), docker_socket=True)

    score = _score.grade(task, run.out_dir)
    record = {"run": run.to_dict(), "score": score.to_dict()}
    (work / "record.json").write_text(json.dumps(record, indent=2))

    print(f"\nexit {run.exit_code}  timed_out={run.timed_out}  "
          f"{run.wall_clock_s / 60:.1f} min")
    verdict = ("UNGRADABLE" if score.passed is None
               else "PASS" if score.passed else "FAIL")
    print(f"{verdict}  {score.metric}="
          f"{'n/a' if score.measured is None else f'{score.measured:.4f}'}"
          f"{'  — ' + score.reason if score.reason else ''}")
    print(f"record   {work / 'record.json'}")
    return 0 if score.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
