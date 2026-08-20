# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Atomic logic for decision-making — turning abstract ideas into executable functions. A modular, privacy-first toolkit built with FastAPI and SQLAlchemy. Five live modules: TCO, PERT, Monte Carlo, EVM, and Bayesian estimation calibration.

The logic repo is the open source foundation of pmo.run — a PMO service combining AI and human expertise. Strategy, audiences, and monetisation: [`docs/STRATEGY.md`](docs/STRATEGY.md). Architecture and technical decisions: [`docs/DESIGN.md`](docs/DESIGN.md). Sprint actuals: [`docs/SPRINT_HISTORY.md`](docs/SPRINT_HISTORY.md). Content pipeline: [`skills/operational/content-cadence/SKILL.md`](skills/operational/content-cadence/SKILL.md).

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

# Run standalone module tests (each module ships its own pytest suite)
pytest examples/standalone/{module}/

# Run standalone example
python examples/standalone/tco/tco.py

# Run the site's parity tests (site/src/lib vs the Python core)
cd site && npm test

# Regenerate the site parity fixtures after changing app/pert or app/tco core
uv run python site/scripts/generate_parity_fixtures.py

# Lint and format
ruff check .
ruff format --check .    # check only
ruff format .            # auto-fix

# Type check (app/ directory only)
pyright

# Security audit (SAST)
opengrep scan --config auto --config .opengrep/ --scan-unknown-extensions .

# Dependency vulnerability scan (SCA)
# Use --config even though the suppression list is currently EMPTY. This is the
# invocation the pre-commit hook and the CI job both use, so it is what
# reproduces them; drop it and you are testing something else.
# It matters the moment a suppression exists again: without the flag the
# auto-discovered root config does not apply to the nested lockfiles, so osv
# reports the project's own waivers as "unused ignores" and then prints them as
# live findings — indistinguishable from expired suppressions, and the tempting
# "fix" is to edit osv-scanner.toml and weaken a control that was working.
# That symptom is dormant, not gone: the Astro 6->7 upgrade discharged all three
# waivers on 2026-07-31, so there is nothing left for it to misreport today.
osv-scanner scan source --config=osv-scanner.toml --recursive .

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
- **Performance** (are we on track?): PERT → Monte Carlo → Baseline → EVM (SV, SPI, CV, CPI) → Bayesian
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
- **Plugin layer (visual UI):** We do not build a visual UI. Enterprises plug in the visual app they already use; Airtable is the reference plugin (the one we dogfood). Work Items represent WBS work packages only (never activities/tasks). Views: timeline, Kanban, dashboard.
- **D1:** Canonical structured store — part of the proprietary data layer we run. Core work-records tables plus analytics tables (activity_analytics, process_events, estimation_log) that plugin UIs never see.
- **R2:** Encrypted blob storage (Zone 1, zero-knowledge). Client uploads, generated reports, audit archives.
- **GitHub webhooks:** Developer activity feeds into D1 via agent. Activity-level analytics are computed by the agent from GitHub events — never manually maintained.

The agent bridges the plugin UI (manager world) and GitHub (developer world), translating between abstraction levels. Managers plan at work package level. Developers work at issue level. The agent computes activity analytics from observed events.

### Privacy: Three-Zone Model

When handling data in module design, be aware of the three zones:

- **Zone 1 (R2):** Zero-knowledge encrypted. Client uploads, generated reports. We can't read it.
- **Zone 2 (Workers memory):** Transient computation. Plaintext exists briefly during report generation, then encrypted.
- **Zone 3 (D1):** Operational metadata. Agent-queryable. Infrastructure-secured, not E2EE.

Never claim "E2EE" without specifying which zone. See strategy doc for full encryption architecture.

### Repository Automation (`automation/`)

`automation/` holds automation that acts **on this repository** rather than shipping as product. It is not imported by `app/`, `mcp_server/` or `site/`, and nothing in the test suite depends on it running.

- **`automation/pr-auditor/`** — an unattended reviewer that comments on every `opened`/`synchronize` pull request. `README.md` is the design document; `reviewer-prompt.md` is the system prompt; `scenario.blueprint.json` is the exported hosted-platform scenario. **It reviews, it does not gate** — it is deliberately not a required context and its token is scoped to comment only, so expect a comment on your own branches and treat it as one reviewer's opinion.
- **The prompt exists twice and cannot drift.** `tests/test_pr_auditor_prompt_parity.py` compares the blueprint's `system` value against `reviewer-prompt.md` byte for byte, and `pytest` is a required context. Edit one without the other and the merge gate goes red.
- **The blueprint can still drift from the live scenario**, because only the prompt is guarded. Re-export after any scenario change; that is currently a rule, not a mechanism.

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
- Ruff lint rules: E, F, FAST, I, N, W, B, C4, UP, SIM (with E501 and B008 ignored)
- **Ruff does not format Markdown, deliberately.** From 0.16 it formats Python code blocks embedded in `.md`, which would rewrite published blog posts (EN and JA), the standalone example READMEs and `skills/montecarlo/SKILL.md` — turning teaching code like `x ** 2` into `x**2`. `[tool.ruff] extend-exclude = ["*.md"]` scopes that out. **Remove it only alongside a deliberate decision to format published content, never to make a red gate go green.** Keep the ruff version in step across all three places it is pinned: the `ruff-pre-commit` rev, the `ruff>=` floor in `pyproject.toml`, and whatever `uv.lock` resolves. They drifted to three different versions once, so local commits and CI ran different formatters.
- Pyright basic mode on `app/` only
- SQLite for development (`logic.db`, gitignored)
- **A gate that skips and a gate that passes render identically.** `ruff` reports `(no files to check) Skipped` on any commit staging no `.py`, and gitleaks in `--staged` mode always prints `0 commits scanned` — in that mode the honest signal is the **bytes** scanned, which read `~0 bytes` for the whole period the hook was silently broken. Never read a green hook as evidence the gate works; plant a canary and watch it go red. **Never add `args` to the gitleaks hook** — pre-commit appends them to the upstream `entry`, which is what broke it.
- Pre-commit hooks: gitleaks, opengrep, osv-scanner, ruff, pyright, pytest, standard hygiene checks. A `commit-msg`-stage hook (`scripts/check-airtable-ids.py`, id `airtable-id-guard`) additionally scans the commit *message*, which gitleaks cannot see. `default_install_hook_types` wires both stages on a plain `pre-commit install` — but **do not set `core.hooksPath`**: pre-commit refuses to install while it is set, so the message guard silently never arrives.

## System Dependencies

The following tools must be installed outside of `uv`:

- `gitleaks` — secret scanning, **8.30.0**, binary release in `~/.local/bin`. **The pre-commit hook and CI each install their own pinned copy, so neither uses your PATH binary** — keep all three in step (`rev` in `.pre-commit-config.yaml`, `GITLEAKS_VERSION` in `ci.yml`, and whatever you installed). **Do not use the `apt` package**: it is 8.16.0, predating the `dir` subcommand entirely, so the documented command fails with `unknown command` and looks like a broken gate rather than a stale binary.
  A manual `gitleaks dir …` scan reports **far more than the gate does, by design**: it walks the filesystem including gitignored files, while the hook scans staged content only. Findings in `CLAUDE.local.md` or `tmp/` are the expected state — both are gitignored, and the identifiers living there rather than in tracked files is the convention working, not a leak. Check `git check-ignore` and `git log --all -- <path>` before treating any of them as an incident.
- `opengrep` — SAST scanning (binary at `~/.local/bin/opengrep`)
- `osv-scanner` — dependency vulnerability scanning (binary at `~/.local/bin/osv-scanner`)

## Key Conventions

- British English in all docs, comments and content (e.g. "analyse", "colour", "maths")
- APA 7th title case for H1 and H2 headings
- Every inline image reference in published markdown (`![...](path)`) must resolve to a real file in the repo. Grep and verify before shipping content.
- **A TypeScript port must match the Python core's rounding *mode*, not only its decimal places.** Python's `round()` is half-to-even; JavaScript's `Math.round` is half-away-from-zero, so `0.625` becomes `0.62` in one and `0.63` in the other. Scaling before rounding (`value * 100`) is also wrong — it manufactures ties the double does not have, so `51.585` rounds down when Python rounds it up. Use `site/src/lib/round.ts`, and net any new port with fixtures generated from the core rather than reading the two implementations side by side; this divergence survived a line-by-line review because places and mode look alike.

## Git workflow

- **GitHub Flow** — always create a `feature/*` branch, push, and open a PR. Never commit directly to `main`.

## Tool Execution Permission Rules

When requesting permission to execute a tool or command, present the following security risks as percentages (%):

- Credential leakage — passwords, secret keys, or API tokens exposed externally
- Data exfiltration — data sent to external servers or third-party endpoints
- Malicious code execution — untrusted code running autonomously
- Environment mutation — PC settings, system config, or dotfiles overwritten

If any risk exceeds 20%, explain the specific vector and proposed mitigation before proceeding.
If any risk exceeds 50%, stop and wait for explicit CEO approval.

This applies to: shell commands, npm/pip installs, file writes outside the repo, network requests to non-allowlisted domains, and any MCP tool invocation that modifies external state.
