# Contributor guidance

Treat [PRODUCT.md](PRODUCT.md), [ARCHITECTURE.md](ARCHITECTURE.md), and the [approved HTML specification](docs/superpowers/specs/2026-08-28-interactive-itinerary-html-design.md) as canonical, in that order for product/architecture and then HTML behavior. `docs/PROJECT_STATUS.md` records progress; the skill and its seven references own runtime workflow.

Do not expand the v0.1 non-goals: no MCP/backend/apps/accounts/sync, offline workflow, built-in PDF pipeline, migrations/partial rebuild, browser automation stack, or eval runner/judge/simulator.

Before editing, inspect the worktree, branch, remotes, status, active references, and relevant tests. Preserve unrelated changes. Use `apply_patch`, follow TDD for behavior changes, run fresh verification, then contribute through a feature branch and PR; do not merge from an implementation task.

Local setup and core checks:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/travel-planner --help
```

Use temporary directories for `init`, `check`, `render`, clean-install, archive, and staged-plugin validation smokes. Never overwrite the committed example merely to test a command.
