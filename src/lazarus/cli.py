"""Lazarus command-line interface.

Currently exposes the commit-era pinner; ``resurrect`` is the eventual
top-level command that runs the full build/repair/contract loop.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

import os

from lazarus import __version__
from lazarus.pinner import pin_requirements


def load_dotenv(path: str = ".env") -> None:
    """Load KEY=VALUE lines from a local .env into the environment.

    Never overrides an already-set variable, and silently no-ops if absent.
    Lets Lazarus pick up ANTHROPIC_API_KEY (the API-credit path) without the
    secret ever being passed on the command line or committed.
    """
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _parse_date(text: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise argparse.ArgumentTypeError(
        f"invalid date {text!r}; expected YYYY-MM-DD"
    )


def _load_requirements(args: argparse.Namespace) -> list[str]:
    reqs: list[str] = list(args.packages or [])
    if args.requirements:
        with open(args.requirements, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    reqs.append(line)
    return reqs


def cmd_pin(args: argparse.Namespace) -> int:
    reqs = _load_requirements(args)
    if not reqs:
        print("no packages given (pass names or --requirements FILE)", file=sys.stderr)
        return 2
    pinned = pin_requirements(reqs, args.date, allow_prerelease=args.pre)
    for name, version in pinned.items():
        if version is None:
            print(f"# {name}: no release on or before {args.date.date()}")
        else:
            print(f"{name}=={version}")
    return 0


def cmd_resurrect(args: argparse.Namespace) -> int:
    import asyncio

    from lazarus.resurrect import Resurrector, ResurrectionEvent

    # Goal: either handed in directly, or drafted by the Scout from a repo URL.
    goal = args.goal
    if args.goal_file:
        with open(args.goal_file, encoding="utf-8") as fh:
            goal = fh.read()

    image = args.image
    gpus = args.gpus
    if not goal:
        if not args.repo_url:
            print("provide a repo URL, or --goal / --goal-file", file=sys.stderr)
            return 2
        from lazarus.scout import scout

        print(f"🔭 Scouting {args.repo_url} — reading the repo + paper to draft a plan…",
              file=sys.stderr, flush=True)
        try:
            plan = asyncio.run(scout(args.repo_url, model=args.model))
        except Exception as exc:  # noqa: BLE001 — surface any planning failure cleanly
            print(f"scout failed: {exc}", file=sys.stderr)
            return 1
        print("\n" + plan.summary() + "\n", file=sys.stderr, flush=True)
        goal = plan.to_goal()
        image = image or plan.base_image
        if gpus is None and plan.needs_gpu:
            gpus = "all"
        if not args.yes:
            if not sys.stdin.isatty():
                print("plan drafted. Re-run with --yes to proceed non-interactively.",
                      file=sys.stderr)
                return 0
            reply = input("Proceed with this resurrection? [y/N] ").strip().lower()
            if reply not in ("y", "yes"):
                print("aborted before spending compute.", file=sys.stderr)
                return 0

    if not image:
        print("no base image: pass --image, or a repo URL so the Scout can pick one",
              file=sys.stderr)
        return 2

    icons = {"text": "\U0001f4ac", "tool_use": "\U0001f527", "tool_result": "\U0001f4e4", "result": "✅"}

    def show(ev: ResurrectionEvent) -> None:
        text = ev.text if len(ev.text) < 600 else ev.text[:600] + "…"
        print(f"{icons.get(ev.kind, ev.kind)} {text}", flush=True)

    r = Resurrector(
        image=image,
        workdir=args.workdir,
        docker_host=args.docker_host,
        max_turns=args.max_turns,
        keep_container=args.keep,
        output_dir=args.out,
        gpus=gpus,
        model=args.model,
        on_event=show,
    )
    res = asyncio.run(r.resurrect(goal))
    print("\n=== resurrection finished ===", file=sys.stderr)
    print(f"completed={res.completed} error={res.is_error} turns={res.num_turns} "
          f"snapshots={res.snapshots}", file=sys.stderr)
    return 0 if (res.completed and not res.is_error) else 1


def cmd_run(args: argparse.Namespace) -> int:
    from lazarus.compose import Pipeline, Registry, Runner

    with open(args.pipeline, encoding="utf-8") as fh:
        pipeline = Pipeline.from_yaml(fh.read())
    registry = Registry.from_dirs(args.registry or ["examples"])
    inputs = {}
    for kv in args.input or []:
        if "=" not in kv:
            print(f"--input must be name=path (got {kv!r})", file=sys.stderr)
            return 2
        name, path = kv.split("=", 1)
        inputs[name] = path
    r = Runner(registry, docker_host=args.docker_host, on_event=lambda m: print(m, flush=True))
    outputs, _ = r.run(pipeline, inputs, args.out)
    print("\n=== pipeline outputs ===", file=sys.stderr)
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lazarus", description=__doc__)
    parser.add_argument("--version", action="version", version=f"lazarus {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_pin = sub.add_parser(
        "pin",
        help="pin dependencies to the versions live on PyPI at a cutoff date",
    )
    p_pin.add_argument("packages", nargs="*", help="requirement strings, e.g. numpy 'scipy>=1'")
    p_pin.add_argument("--date", required=True, type=_parse_date, help="cutoff date YYYY-MM-DD")
    p_pin.add_argument("--requirements", help="path to a requirements.txt to pin")
    p_pin.add_argument("--pre", action="store_true", help="allow prerelease versions")
    p_pin.set_defaults(func=cmd_pin)

    p_res = sub.add_parser("resurrect", help="drive an autonomous resurrection loop in a sandbox")
    p_res.add_argument("repo_url", nargs="?", help="a GitHub URL to resurrect from scratch (the Scout writes the goal + picks a base image)")
    p_res.add_argument("--image", help="base container image to resurrect in (overrides the Scout's pick)")
    p_res.add_argument("--goal", help="what to resurrect and how to prove it (skips the Scout)")
    p_res.add_argument("--goal-file", help="read the goal from a file (skips the Scout)")
    p_res.add_argument("--yes", "-y", action="store_true", help="don't pause to confirm the Scout's plan before spending compute")
    p_res.add_argument("--workdir", default="/work", help="working dir inside the container")
    p_res.add_argument("--docker-host", default=None, help="e.g. ssh://user@host to run remotely")
    p_res.add_argument("--max-turns", type=int, default=80)
    p_res.add_argument("--model", default=None, help="model for the Scout + resurrection agent (default: SDK default)")
    p_res.add_argument("--keep", action="store_true", help="keep the container after finishing")
    p_res.add_argument("--out", default="lazarus-output", help="dir for the emitted integration package")
    p_res.add_argument("--gpus", default=None, help="pass GPUs to the container, e.g. 'all' (needs nvidia-container-toolkit)")
    p_res.set_defaults(func=cmd_resurrect)

    p_run = sub.add_parser("run", help="run a pipeline composing resurrected components")
    p_run.add_argument("pipeline", help="pipeline YAML file")
    p_run.add_argument("--input", action="append", help="pipeline input as name=path (repeatable)")
    p_run.add_argument("--registry", action="append", help="dir(s) of component contracts (default: examples/)")
    p_run.add_argument("--docker-host", default=None, help="e.g. ssh://user@host to run on a remote/GPU box")
    p_run.add_argument("--out", default="pipeline-output", help="output directory")
    p_run.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
