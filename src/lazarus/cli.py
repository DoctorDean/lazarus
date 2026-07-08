"""Lazarus command-line interface.

Currently exposes the commit-era pinner; ``resurrect`` is the eventual
top-level command that runs the full build/repair/contract loop.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from lazarus import __version__
from lazarus.pinner import pin_requirements


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

    goal = args.goal
    if args.goal_file:
        with open(args.goal_file, encoding="utf-8") as fh:
            goal = fh.read()
    if not goal:
        print("provide --goal or --goal-file", file=sys.stderr)
        return 2

    icons = {"text": "\U0001f4ac", "tool_use": "\U0001f527", "tool_result": "\U0001f4e4", "result": "✅"}

    def show(ev: ResurrectionEvent) -> None:
        text = ev.text if len(ev.text) < 600 else ev.text[:600] + "…"
        print(f"{icons.get(ev.kind, ev.kind)} {text}", flush=True)

    r = Resurrector(
        image=args.image,
        workdir=args.workdir,
        docker_host=args.docker_host,
        max_turns=args.max_turns,
        keep_container=args.keep,
        on_event=show,
    )
    res = asyncio.run(r.resurrect(goal))
    print("\n=== resurrection finished ===", file=sys.stderr)
    print(f"completed={res.completed} error={res.is_error} turns={res.num_turns} "
          f"snapshots={res.snapshots}", file=sys.stderr)
    return 0 if (res.completed and not res.is_error) else 1


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
    p_res.add_argument("--image", required=True, help="base container image to resurrect in")
    p_res.add_argument("--goal", help="what to resurrect and how to prove it")
    p_res.add_argument("--goal-file", help="read the goal from a file")
    p_res.add_argument("--workdir", default="/work", help="working dir inside the container")
    p_res.add_argument("--docker-host", default=None, help="e.g. ssh://user@host to run remotely")
    p_res.add_argument("--max-turns", type=int, default=80)
    p_res.add_argument("--keep", action="store_true", help="keep the container after finishing")
    p_res.set_defaults(func=cmd_resurrect)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
