# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Atomic logic for decision-making — turning abstract ideas into executable functions. A modular, privacy-first toolkit built with FastAPI and SQLAlchemy. Currently features a TCO (Total Cost of Ownership) calculator; NPV, IRR, PERT, and other modules are planned.

The logic repo is the open source foundation of pmo.run — a PMO service combining AI and human expertise. Full strategy, architecture, and roadmap: [`docs/PMO_RUN_STRATEGY.md`](docs/PMO_RUN_STRATEGY.md).

## Commands

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Run API server (hot reload)
uv run uvicorn app.main:app --reload

# Run all tests
pytest

# Run a single test file
pytest tests/test_foo.py

# Run standalone example
python examples/standalone/tco/tco.py

# Lint and format
ruff check .
ruff format --check .    # check only
ruff format .            # auto-fix

# Type check (app/ directory only)
pyright

# Security audit
bandit -c pyproject.toml -r .

# Run all pre-commit hooks
pre-commit run --all-files
```

## Architecture

Each feature module (e.g., `app/tco/`) follows a consistent layered pattern:

- **`core.py`** — Pure calculation functions. No FastAPI or DB dependencies. This is the atomic logic layer. **Always MIT licensed, always public.**
- **`router.py`** — FastAPI endpoints. Stateless endpoints call `core.py` directly; stateful endpoints go through `crud.py`.
- **`schemas.py`** — Pydantic models for request/response validation.
- **`models.py`** — SQLAlchemy ORM models (inherits `Base` from `app/database.py`).
- **`crud.py`** — Database operations. Calls `core.py` to compute values before persisting.

`app/main.py` is the FastAPI entry point that mounts feature routers. `app/database.py` provides the shared SQLAlchemy engine, session factory, and `Base`.

`examples/standalone/` contains self-contained library versions of modules (pure Python, optional pandas/matplotlib).

### Plugin Architecture

Modules support an optional calibration layer for field-tested adjustments:

- **`core.py`** — Pure math (OSS). The formula itself.
- **`calibration.py`** — Plugin interface for field adjustments (OSS). Defines what can be calibrated.
- **`plugins/`** — Proprietary calibration data (closed, not in this repo). Industry-specific coefficients, risk profiles, delay factors derived from consulting experience.

The boundary is clear: **logic and code are public, calibration data and reasoning models are proprietary.** When developing new modules, always ensure `core.py` works standalone without any plugin. The plugin layer enhances precision, never gates functionality.

## Module Development Flow

Every new module follows this pipeline:

1. **Standalone PoC** in `examples/standalone/{module}/` — pure Python, no dependencies
2. **FastAPI integration** in `app/{module}/` — following the layered pattern above
3. **Plugin interface** in `app/{module}/calibration.py` — optional, defines calibration points
4. **Tests** in `tests/{module}/` — comprehensive, including edge cases
5. **Content** — blog post explaining the problem, math, and solution (see strategy doc)

## Code Style

- Python 3.14, managed with `uv`
- Ruff: 100 char line length, double quotes, spaces for indentation
- Ruff lint rules: E, F, I, N, W, B, C4, UP, SIM (with E501 and B008 ignored)
- Pyright basic mode on `app/` only
- SQLite for development (`logic.db`, gitignored)
- Pre-commit hooks: gitleaks, bandit, ruff, pyright, pytest, standard hygiene checks

## Git workflow

- **GitHub Flow** — always create a `feature/*` branch, push, and open a PR. Never commit directly to `main`.
