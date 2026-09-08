"""Small internal CLI for deterministic Travel Planner helpers."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import yaml

from . import __version__
from .checks import CheckReport, run_checks
from .render.html import DEFAULTS as HTML_DEFAULTS
from .render.html import render_html, write_rendered_html
from .render.media import load_media
from .render.viewmodel import build_view
from .state import load_trip, validate_trip
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

    check = commands.add_parser("check", help="Check recorded data integrity")
    check.add_argument("path", type=Path)

    render = commands.add_parser("render", help="Render the shared HTML itinerary")
    render.add_argument("path", type=Path)
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--at", type=datetime.fromisoformat, required=True)

    return parser


def _structural_report(path: Path) -> CheckReport | None:
    validation = validate_trip(path)
    if validation.ok:
        return None
    return CheckReport(validation.issues, (), (), ())


def _print_report(report: CheckReport) -> None:
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    """Run one of the three internal helper commands."""
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

    if args.command == "check":
        structural = _structural_report(args.path)
        if structural is not None:
            _print_report(structural)
            return 2
        report = run_checks(load_trip(args.path))
        _print_report(report)
        return 0 if report.ok else 3

    if args.command == "render":
        structural = _structural_report(args.path)
        if structural is not None:
            _print_report(structural)
            return 2
        try:
            state = load_trip(args.path)
            report = run_checks(state)
            if not report.ok:
                _print_report(report)
                return 3
            media = load_media(state)
            html = render_html(build_view(state, report, args.at), media, HTML_DEFAULTS)
            write_rendered_html(html, args.output)
        except (ValueError, OSError) as error:
            print(str(error), file=sys.stderr)
            return 2
        print(f"Rendered HTML: {args.output}")
        return 0

    _parser().print_help()
    return 2
