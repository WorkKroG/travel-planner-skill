"""Command-line entry point for deterministic Travel Planner helpers."""

from . import __version__


def main() -> int:
    """Print the installed helper version."""
    print(f"travel-planner {__version__}")
    return 0
