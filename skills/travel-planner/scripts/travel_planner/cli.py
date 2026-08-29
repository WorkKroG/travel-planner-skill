"""Command-line entry point for deterministic Travel Planner helpers."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import yaml

from . import __version__
from .challenge import run_challenge
from .impact import analyze_change
from .maps import MapPlace, build_place_url, load_map_policy, select_provider
from .migration import MigrationError, apply_migration, preview_migration
from .render.html import DEFAULTS as HTML_DEFAULTS
from .render.html import write_html
from .render.markdown import render_markdown
from .render.pdf import render_pdf
from .render.qa import (
    attest_document,
    attestation_path,
    load_attestation,
    run_document_qa,
    write_attestation,
)
from .render.viewmodel import build_view
from .state import load_trip, validate_trip
from .workspace import PROJECT_REMINDER, WorkspaceError, initialize_trip

_FINAL_STATUS_CLASS = re.compile(
    r"<[^>]*\bclass\s*=\s*(['\"])[^'\"]*\bdocument-status--final\b[^'\"]*\1",
    re.IGNORECASE,
)


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
    render = commands.add_parser("render", help="Render a derived itinerary document")
    render.add_argument("path", type=Path)
    render.add_argument("--format", choices=("markdown", "html"), required=True)
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--at", type=datetime.fromisoformat, required=True)
    finalize = commands.add_parser("finalize", help="QA and publish an exact Final HTML artifact")
    finalize.add_argument("path", type=Path)
    finalize.add_argument("--output", type=Path, required=True)
    finalize.add_argument("--at", type=datetime.fromisoformat, required=True)
    finalize.add_argument(
        "--profiles",
        default="phone,tablet,desktop,narrow",
        help="Comma-separated browser profiles",
    )
    pdf = commands.add_parser("pdf", help="Create a PDF from a rendered HTML document")
    pdf.add_argument("html", type=Path)
    pdf.add_argument("--output", type=Path, required=True)
    qa = commands.add_parser("qa", help="Run browser quality gates for a rendered HTML document")
    qa.add_argument("html", type=Path)
    qa.add_argument(
        "--profiles",
        default="phone,tablet,desktop,narrow",
        help="Comma-separated browser profiles",
    )
    return parser


def _profiles(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _write_draft_html(state, challenge, generated_at: datetime, output: Path) -> None:
    write_html(build_view(state, challenge, generated_at), output, HTML_DEFAULTS)
    attestation_path(output).unlink(missing_ok=True)


def _staging_path(destination: Path, suffix: str) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=suffix, dir=destination.parent
    )
    os.close(descriptor)
    path = Path(temporary_name)
    path.unlink(missing_ok=True)
    return path


def _fsync_file(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def _has_final_status(html_path: Path) -> bool:
    try:
        return bool(_FINAL_STATUS_CLASS.search(Path(html_path).read_text(encoding="utf-8")))
    except OSError:
        return False


def _publish_final(candidate: Path, receipt, output: Path) -> bool:
    """Publish matching Final HTML and receipt, restoring only safe prior artifacts on failure."""
    receipt_output = attestation_path(output)
    receipt_stage = _staging_path(receipt_output, ".json")
    output_backup = _staging_path(output, ".backup")
    receipt_backup = _staging_path(receipt_output, ".backup")
    had_output = output.is_file()
    had_receipt = receipt_output.is_file()
    moved_output = False
    moved_receipt = False
    published_receipt = False
    published_output = False
    try:
        _fsync_file(candidate)
        write_attestation(candidate, receipt, destination=receipt_stage)
        if had_output:
            output.replace(output_backup)
            moved_output = True
        if had_receipt:
            receipt_output.replace(receipt_backup)
            moved_receipt = True
        receipt_stage.replace(receipt_output)
        published_receipt = True
        candidate.replace(output)
        published_output = True
        return True
    except (OSError, ValueError):
        if published_output:
            output.unlink(missing_ok=True)
        if published_receipt:
            receipt_output.unlink(missing_ok=True)
        if moved_receipt:
            try:
                receipt_backup.replace(receipt_output)
            except OSError:
                receipt_output.unlink(missing_ok=True)
        if moved_output and not _has_final_status(output_backup):
            try:
                output_backup.replace(output)
            except OSError:
                output.unlink(missing_ok=True)
        return False
    finally:
        receipt_stage.unlink(missing_ok=True)
        output_backup.unlink(missing_ok=True)
        receipt_backup.unlink(missing_ok=True)


def _publish_draft_after_failure(state, challenge, generated_at: datetime, output: Path) -> None:
    """Prefer a current Draft after a failed Final publication; never leave an unreceipted Final."""
    try:
        _write_draft_html(state, challenge, generated_at, output)
    except (OSError, ValueError):
        if _has_final_status(output):
            try:
                output.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            attestation_path(output).unlink(missing_ok=True)
        except OSError:
            pass


def _finalize_html(path: Path, output: Path, generated_at: datetime, profiles: tuple[str, ...]) -> int:
    report = validate_trip(path)
    if not report.ok:
        for issue in report.issues:
            print(f"{issue.path}: {issue.message}", file=sys.stderr)
        return 2
    state = load_trip(path)
    challenge = run_challenge(state, "detailed", generated_at)
    candidate = build_view(state, challenge, generated_at, qa_attested=True)
    candidate_path: Path | None = None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        if candidate.status != "final":
            _write_draft_html(state, challenge, generated_at, output)
            print(
                "Final status requires requested final state, a frozen route, and a passing challenge.",
                file=sys.stderr,
            )
            return 5

        candidate_path = _staging_path(output, ".html")
        write_html(candidate, candidate_path, HTML_DEFAULTS)
        qa_report = run_document_qa(candidate_path, profiles)
        if not qa_report.final_allowed:
            _write_draft_html(state, challenge, generated_at, output)
            print(json.dumps(qa_report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True), file=sys.stderr)
            return 5
        receipt = attest_document(candidate_path, qa_report)
        if not _publish_final(candidate_path, receipt, output):
            _publish_draft_after_failure(state, challenge, generated_at, output)
            print("Final publication failed; no unreceipted Final artifact was published.", file=sys.stderr)
            return 5
    except (OSError, ValueError) as error:
        _publish_draft_after_failure(state, challenge, generated_at, output)
        print(f"Final publication failed: {error}", file=sys.stderr)
        return 5
    finally:
        if candidate_path is not None:
            try:
                candidate_path.unlink(missing_ok=True)
            except OSError:
                pass
    print(f"Finalized HTML: {output}")
    return 0


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
    if args.command == "render":
        report = validate_trip(args.path)
        if not report.ok:
            for issue in report.issues:
                print(f"{issue.path}: {issue.message}", file=sys.stderr)
            return 2
        state = load_trip(args.path)
        challenge = run_challenge(state, "detailed", args.at)
        view = build_view(state, challenge, args.at)
        if args.format == "html":
            write_html(view, args.output, HTML_DEFAULTS)
        else:
            document = render_markdown(view)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(document, encoding="utf-8")
        print(f"Rendered {args.format}: {args.output}")
        return 0
    if args.command == "finalize":
        return _finalize_html(args.path, args.output, args.at, _profiles(args.profiles))
    if args.command == "pdf":
        if _has_final_status(args.html):
            receipt = load_attestation(args.html)
            if receipt is None or not receipt.matches(args.html):
                print("Final HTML requires a matching successful QA attestation before PDF export.", file=sys.stderr)
                return 4
        result = render_pdf(args.html, args.output)
        stream = sys.stdout if result.created else sys.stderr
        print(f"{result.code}: {result.message}", file=stream)
        return 0 if result.created else 4
    if args.command == "qa":
        report = run_document_qa(args.html, _profiles(args.profiles))
        print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report.final_allowed else 5
    _parser().print_help()
    return 2
