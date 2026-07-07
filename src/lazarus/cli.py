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
    print(
        "lazarus resurrect is not wired up yet — the build/repair/contract "
        "loop lands in a later slice. For now, try `lazarus pin`.",
        file=sys.stderr,
    )
    return 1


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

    p_res = sub.add_parser("resurrect", help="(coming soon) resurrect a repo end to end")
    p_res.add_argument("repo", help="git URL or local path of the repo to resurrect")
    p_res.set_defaults(func=cmd_resurrect)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
