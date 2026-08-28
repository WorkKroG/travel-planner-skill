"""Command-line entry point for deterministic Travel Planner helpers."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from . import __version__
from .state import validate_trip
from .workspace import PROJECT_REMINDER, WorkspaceError, initialize_trip


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="travel-planner")
    parser.add_argument("--version", action="store_true")
    commands = parser.add_subparsers(dest="command")
    init = commands.add_parser("init", help="Create a new trip workspace")
    init.add_argument("path", type=Path)
    init.add_argument("--title", required=True)
    init.add_argument("--trip-id")
    init.add_argument("--confirm-path", action="store_true")
    validate = commands.add_parser("validate", help="Validate a trip workspace")
    validate.add_argument("path", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested deterministic helper command."""
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if not arguments:
        print(f"travel-planner {__version__}")
        return 0
    args = _parser().parse_args(arguments)
    if args.version:
        print(f"travel-planner {__version__}")
        return 0
    if args.command == "init":
        if not args.confirm_path:
            print(PROJECT_REMINDER, file=sys.stderr)
            return 2
        try:
            paths = initialize_trip(args.path, args.title, args.trip_id)
        except WorkspaceError as error:
            print(str(error), file=sys.stderr)
            return 2
        trip_id = yaml.safe_load(paths.brief.read_text(encoding="utf-8"))["trip_id"]
        print(f"Initialized trip {trip_id} at {paths.root}")
        return 0
    if args.command == "validate":
        report = validate_trip(args.path)
        if report.ok:
            print(f"Trip state is valid: {args.path}")
            return 0
        for issue in report.issues:
            print(f"{issue.path}: {issue.message}", file=sys.stderr)
        return 2
    _parser().print_help()
    return 2
