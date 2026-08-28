"""Command-line entry point for deterministic Travel Planner helpers."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import yaml

from . import __version__
from .challenge import run_challenge
from .impact import analyze_change
from .maps import MapPlace, build_place_url, load_map_policy, select_provider
from .migration import MigrationError, apply_migration, preview_migration
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
    validate = commands.add_parser("validate", help="Validate a trip workspace")
    validate.add_argument("path", type=Path)
    challenge = commands.add_parser("challenge", help="Run deterministic trip checks")
    challenge.add_argument("path", type=Path)
    challenge.add_argument("--stage", choices=("skeleton", "detailed"), required=True)
    challenge.add_argument("--at", type=datetime.fromisoformat, required=True)
    map_link = commands.add_parser("map-link", help="Build a destination-aware map link")
    map_link.add_argument("--country", required=True)
    map_link.add_argument("--query", required=True)
    map_link.add_argument("--provider", choices=("auto", "yandex", "google"), default="auto")
    map_link.add_argument("--latitude", type=float)
    map_link.add_argument("--longitude", type=float)
    impact = commands.add_parser("impact", help="Preview partial rebuild targets")
    impact.add_argument("before", type=Path)
    impact.add_argument("after", type=Path)
    migrate = commands.add_parser("migrate", help="Preview or apply a state schema migration")
    migrate.add_argument("path", type=Path)
    migrate.add_argument("--target-version", type=int, required=True)
    migrate.add_argument("--confirm", action="store_true")
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
    if args.command == "challenge":
        report = run_challenge(load_trip(args.path), args.stage, args.at)
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report.hard_pass else 3
    if args.command == "map-link":
        try:
            place = MapPlace(
                args.query,
                args.country,
                latitude=args.latitude,
                longitude=args.longitude,
            )
            provider = select_provider(args.country, args.provider, load_map_policy())
            url = build_place_url(provider, place)
        except (FileNotFoundError, TypeError, ValueError) as error:
            print(str(error), file=sys.stderr)
            return 2
        print(f"{provider.value.title()} Maps: {url}")
        return 0
    if args.command == "impact":
        report = analyze_change(load_trip(args.before), load_trip(args.after))
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "migrate":
        try:
            plan = preview_migration(args.path, args.target_version)
            print(json.dumps(plan.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
            if args.confirm:
                apply_migration(plan, confirmed=True)
                print(f"Migration applied; backup: {plan.backup_root}")
        except (MigrationError, OSError, TypeError, yaml.YAMLError) as error:
            print(str(error), file=sys.stderr)
            return 2
        return 0
    _parser().print_help()
    return 2
