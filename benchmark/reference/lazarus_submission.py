#!/usr/bin/env python3
"""Lazarus packaged as a benchmark submission — the reference implementation.

This is the bridge between two things that don't line up on their own. Lazarus emits a
**contract** (a container plus `lazarus.yaml` that runs a revived method); a benchmark task
wants a **specific output file** in `/out`. Something has to translate, and *where* that
translation lives is the whole design question.

It lives here, in the goal — not in a per-task adapter. A wrapper that reshaped
ScanNet's ``predictions_receptor_A.csv`` into the task's ``resid,score`` would be the
harness doing the submission's work, and it would have to grow a branch per task. Instead
the task's requirements are handed to the agent, which is exactly what
``SUBMISSION.md`` asks of *every* submission: read ``output_schema``, write that file.

The other deliberate split: **the Scout plans, the task judges.** Scout still picks the
base image and decides whether a GPU is needed — that is its job and it reads only the
public repo. But the goal's success criterion comes from the *task*, never from the
Scout's own invented sanity metric. Letting the agent keep authoring its own bar is the
§2.1 problem the whole benchmark exists to remove.

Run inside the submission image::

    lazarus_submission.py --repo-url <url> --commit <sha> --task /task/task.yaml --out /out

Needs a Docker socket (it drives containers to do the revival) and ``ANTHROPIC_API_KEY``.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import yaml


def _fetch_instructions(repo_url: str, commit: str = "",
                        artifact_url: str = "", artifact_sha256: str = "") -> str:
    """How to obtain the source *at the pin*. Never HEAD."""
    if commit:
        return (
            f"    git clone {repo_url} repo && cd repo && git checkout {commit}\n"
            f"You MUST end up on commit {commit}. Do not use `git clone --depth 1` without\n"
            f"a following fetch of that exact commit — a shallow clone of HEAD will not\n"
            f"contain it, and HEAD is not what is being measured.\n")
    return (
        f"    curl -L -o source.archive {artifact_url}\n"
        f"    echo '{artifact_sha256}  source.archive' | sha256sum -c -\n"
        f"The checksum MUST verify before you unpack it. This source is not in git; the\n"
        f"hash is the pin.\n")


def build_goal(task: dict, repo_url: str, *, commit: str = "",
               artifact_url: str = "", artifact_sha256: str = "") -> str:
    """Turn a (redacted) task spec into the instruction handed to the resurrection loop.

    Pure and unit-tested: this is the one place the benchmark's requirements become the
    agent's objective, so it must state the pin, the input, and the exact output contract
    without inventing a success criterion of its own.
    """
    ev = task.get("evaluation") or {}
    out_path = task.get("output_path") or "prediction.csv"
    schema = task.get("output_schema") or []
    schema_line = (f"a CSV with the header `{','.join(schema)}` (one row per item)"
                   if schema else f"the format described above for `{out_path}`")

    if task.get("kind") == "reproduce":
        criterion = (
            f"Report the value of `{ev.get('metric', 'the metric')}` that the method\n"
            f"actually achieves on the benchmark shipped with the repo. Write it to\n"
            f"/out/{out_path} as `{ev.get('metric', 'metric')}=<value>` and nothing else.\n"
            f"Do NOT write a value you did not measure: the number is compared against the\n"
            f"paper's, and a guess that happens to land inside the band is indistinguishable\n"
            f"from fraud. If you cannot run the benchmark, write no file.\n")
    else:
        direction = ev.get("direction", "")
        bar = ev.get("threshold")
        target = (f"You are judged on `{ev.get('metric')}` "
                  f"({'higher' if direction == 'higher' else 'lower'} is better"
                  + (f", target {'≥' if direction == 'higher' else '≤'} {bar}" if bar is not None else "")
                  + ").\n") if ev.get("metric") else ""
        criterion = (
            f"{target}"
            f"Run the revived method on the input in /task/input and write its predictions\n"
            f"to /out/{out_path} as {schema_line}.\n"
            f"Every item in the input must appear exactly once. The grader joins rows by\n"
            f"their id column, so row order does not matter, but ids must match the input\n"
            f"and values must be finite numbers.\n")

    return (
        f"Revive this repository and use it to produce one output file.\n\n"
        f"REPOSITORY: {repo_url}\n\n"
        f"FIRST, get the source at the pinned version:\n"
        f"{_fetch_instructions(repo_url, commit, artifact_url, artifact_sha256)}\n"
        f"CAPABILITY TO REVIVE:\n{task.get('capability', '').strip()}\n\n"
        f"WHAT TO PRODUCE:\n{criterion}\n"
        f"NOTES:\n"
        f"- /task is read-only; /out is where your result must land.\n"
        f"- Repair whatever is broken: pin era-appropriate dependencies, fix imports,\n"
        f"  replace rotted download URLs, build missing binaries. That is the task.\n"
        f"- Do not invent your own success metric or relax the one above. The output file\n"
        f"  is graded outside this container against data you cannot see.\n"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Lazarus as a benchmark submission")
    ap.add_argument("--repo-url", required=True)
    ap.add_argument("--commit", default="")
    ap.add_argument("--artifact-url", default="")
    ap.add_argument("--artifact-sha256", default="")
    ap.add_argument("--task", required=True, help="path to the (redacted) task.yaml")
    ap.add_argument("--out", required=True)
    ap.add_argument("--image", default=None, help="skip the Scout and use this base image")
    ap.add_argument("--max-turns", type=int, default=90)
    ap.add_argument("--model", default=None)
    args = ap.parse_args(argv)

    if not args.commit and not (args.artifact_url and args.artifact_sha256):
        print("need --commit, or --artifact-url with --artifact-sha256", file=sys.stderr)
        return 2

    task = yaml.safe_load(Path(args.task).read_text()) or {}
    goal = build_goal(task, args.repo_url, commit=args.commit,
                      artifact_url=args.artifact_url,
                      artifact_sha256=args.artifact_sha256)

    from lazarus.resurrect import Resurrector

    image, gpus = args.image, None
    if image is None:
        # Scout picks the base image and the GPU need — its job, from the public repo only.
        # The success criterion is NOT taken from its plan; that comes from the task.
        from lazarus.scout import scout
        try:
            plan = asyncio.run(scout(args.repo_url, model=args.model))
            image, gpus = plan.base_image, ("all" if plan.needs_gpu else None)
        except Exception as exc:  # noqa: BLE001
            print(f"scout failed: {exc}", file=sys.stderr)
            return 3

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    r = Resurrector(image=image, max_turns=args.max_turns, model=args.model,
                    gpus=gpus, output_dir=str(out / "_contract"),
                    on_event=lambda e: print(f"{e.kind}: {e.text[:200]}", flush=True))
    result = asyncio.run(r.resurrect(goal))

    produced = out / (task.get("output_path") or "prediction.csv")
    print(json.dumps({"completed": bool(result and result.completed),
                      "turns": getattr(result, "num_turns", None),
                      "wrote_output": produced.exists()}))
    # Exit non-zero only if nothing was produced. A crash after a correct write still
    # counts — the harness grades the artifact, not the exit code.
    return 0 if produced.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
