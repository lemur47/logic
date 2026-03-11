# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Atomic logic for decision-making — turning abstract ideas into executable functions. A modular, privacy-first toolkit built with FastAPI and SQLAlchemy. Currently features a TCO (Total Cost of Ownership) calculator with PERT, EVM, and other modules planned.

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

### Module Families

Modules are organised into three families that correspond to PMO decision questions:

- **Finance** (is it worth it?): TCO → NPV → IRR → ROI
- **Performance** (are we on track?): PERT → Baseline → EVM (SV, SPI, CV, CPI) → Bayesian
- **Value Delivery** (are we delivering?): Flow Metrics → Benefits Realisation

All families feed into the agent's decision traceability layer. When building a new module, identify which family it belongs to and how it connects to adjacent modules.

### Plugin Architecture

Modules support an optional calibration layer for field-tested adjustments:

- **`core.py`** — Pure math (OSS). The formula itself.
- **`calibration.py`** — Plugin interface for field adjustments (OSS). Defines what can be calibrated.
- **`plugins/`** — Proprietary calibration data (closed, not in this repo). Industry-specific coefficients, risk profiles, delay factors derived from consulting experience.

The boundary is clear: **logic and code are public, calibration data and reasoning models are proprietary.** When developing new modules, always ensure `core.py` works standalone without any plugin. The plugin layer enhances precision, never gates functionality.

`plugins/` directories are gitignored in this repo. Proprietary calibration data is managed separately and never committed to the public repository.

### Product Architecture Context

This repo is one layer of a larger system. Understanding the full picture helps when making design decisions:

- **This repo (logic):** Pure math modules + FastAPI endpoints. Python. MIT licensed. Community-facing.
- **Cloudflare Agent (future):** TypeScript port of these modules. Agents SDK, Workers, D1/R2. Product-facing.
- **Baserow:** Relational visual database. Operational UI for managers. Work Items represent WBS work packages only (never activities/tasks). Views: timeline, Kanban, dashboard.
- **D1:** Structured metadata store. Mirrors Baserow core tables plus analytics tables (activity_analytics, process_events, estimation_log) that Baserow never sees.
- **R2:** Encrypted blob storage (Zone 1, zero-knowledge). Client uploads, generated reports, audit archives.
- **GitHub webhooks:** Developer activity feeds into D1 via agent. Activity-level analytics are computed by the agent from GitHub events — never manually maintained.

The agent bridges Baserow (manager world) and GitHub (developer world), translating between abstraction levels. Managers plan at work package level. Developers work at issue level. The agent computes activity analytics from observed events.

### Privacy: Three-Zone Model

When handling data in module design, be aware of the three zones:

- **Zone 1 (R2):** Zero-knowledge encrypted. Client uploads, generated reports. We can't read it.
- **Zone 2 (Workers memory):** Transient computation. Plaintext exists briefly during report generation, then encrypted.
- **Zone 3 (D1):** Operational metadata. Agent-queryable. Infrastructure-secured, not E2EE.

Never claim "E2EE" without specifying which zone. See strategy doc for full encryption architecture.

## Module Development Flow

Every new module follows this pipeline:

1. **Standalone PoC** in `examples/standalone/{module}/` — pure Python, no dependencies
2. **FastAPI integration** in `app/{module}/` — following the layered pattern above
3. **Plugin interface** in `app/{module}/calibration.py` — optional, defines calibration points
4. **Tests** in `tests/{module}/` — comprehensive, including edge cases
5. **Content** — blog post explaining the problem, maths, and solution (see strategy doc)

## Code Style

- Python 3.14, managed with `uv`
- Ruff: 100 char line length, double quotes, spaces for indentation
- Ruff lint rules: E, F, I, N, W, B, C4, UP, SIM (with E501 and B008 ignored)
- Pyright basic mode on `app/` only
- SQLite for development (`logic.db`, gitignored)
- Pre-commit hooks: gitleaks, bandit, ruff, pyright, pytest, standard hygiene checks

## Key Conventions

- British English in all docs, comments and content (e.g. "analyse", "colour", "maths")

## Git workflow

- **GitHub Flow** — always create a `feature/*` branch, push, and open a PR. Never commit directly to `main`.
