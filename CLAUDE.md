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

# Run the remote-MCP example's parity tests (examples/remote-mcp/src vs the core)
cd examples/remote-mcp && npm test

# Build the site. NOT optional when you have touched site/ — `npm test` covers the
# parity net and the crawlability gate's parsing, but the gate itself only runs
# after `astro build`, because what it checks does not exist until then. CI runs
# `npm test` BEFORE `npm run build`, so a green test run says nothing about it.
cd site && npm run build

# Regenerate BOTH parity fixture sets after changing app/pert or app/tco core.
# The pytest CI job re-runs these and fails on a non-empty diff, so a core change
# that leaves the fixtures behind now goes red instead of quietly netting the two
# TypeScript ports against a core that no longer exists.
uv run python site/scripts/generate_parity_fixtures.py
uv run python examples/remote-mcp/scripts/generate_fixtures.py

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

- **`automation/pr-auditor/`** — an unattended reviewer that comments on `opened`/`synchronize` pull requests. `README.md` is the design document; `reviewer-prompt.md` is the system prompt; `scenario.blueprint.json` is the exported hosted-platform scenario. **It reviews, it does not gate** — it is deliberately not a required context and its token is scoped to comment only, so expect a comment on your own branches and treat it as one reviewer's opinion.
- **Commenting is not yet unconditional, so silence is ambiguous.** This line previously read "comments on every `opened`/`synchronize` pull request". The diff fetch stops on an HTTP error with no error branch, so a GitHub `406` on a sufficiently large pull request produces **no comment and no usage row at all** — indistinguishable from the auditor being off. Do not read a missing comment as a clean review. Scoped as Sprint 18 work.
- **The *system* prompt exists twice and cannot drift.** `tests/test_pr_auditor_prompt_parity.py` compares the blueprint's `system` value against `reviewer-prompt.md` byte for byte, and `pytest` is a required context. Edit one without the other and the merge gate goes red.
- **The user turn is NOT guarded, and that is where the delimiters live.** The untrusted-diff markers, the truncation header count and the cut-off notice sit in the user message, which no test asserts on. That pairing drifted twice inside a single pull request. Read "only the prompt is guarded" narrowly: it means the system field, not the reviewer's instructions as a whole.
- **The blueprint can still drift from the live scenario.** Re-export after any scenario change; that is currently a rule, not a mechanism.

## Module Development Flow

Every new module follows this pipeline. **Testing is not the fourth step of it.**
Steps 1 and 2 are each written test-first; step 4 is the comprehensive pass, not
the first one.

1. **Standalone PoC** in `examples/standalone/{module}/` — pure Python, no dependencies. **It ships its own pytest suite**, and `pytest examples/standalone/{module}/` passing is what makes the PoC done. All five existing modules already work this way; the Commands section above documents the invocation.
2. **FastAPI integration** in `app/{module}/` — following the layered pattern above
3. **Plugin interface** in `app/{module}/calibration.py` — optional, defines calibration points
4. **Tests** in `tests/{module}/` — the comprehensive pass: edge cases, and parity against `core.py` for every surface that re-implements it
5. **Content** — blog post explaining the problem, maths, and solution (see strategy doc)

### Write the Cognition Test-First

A module's `core.py` is a piece of reasoning expressed as code, and the shape of
the function *is* the decision being made. Write those test-first: state the
contract, write the test, watch it fail **for the reason you stated**, then
implement. The same applies to anything else where the shape is the decision — a
new MCP tool or endpoint, a schema or vocabulary, a projection, an auditor check,
or the logic of a privacy control.

**Do not** work this way for mechanical edits, renames or formatting, and
**especially not for infrastructure controls** — CI gates, scanners, hooks. Those
fail by *silence* rather than by returning a wrong answer, so a passing test
proves nothing about them. Plant a canary and watch it go red instead; the dead
gitleaks hook is the worked example, recorded under Code Style below.

The `tdd-loop` skill and its `/tdd` command drive the loop. **They ship from the
separate `agent-ops` repository, not from this one**, and reach a working copy by
symlink — so a fresh clone of `logic` will not have them. The practice is the
requirement; the tooling is a convenience.

## Code Style

- Python 3.14, managed with `uv`
- Ruff: 100 char line length, double quotes, spaces for indentation
- Ruff lint rules: E, F, FAST, I, N, W, B, C4, UP, SIM (with E501 and B008 ignored)
- **Ruff does not format Markdown, deliberately.** From 0.16 it formats Python code blocks embedded in `.md`, which would rewrite published blog posts (EN and JA), the standalone example READMEs and `skills/montecarlo/SKILL.md` — turning teaching code like `x ** 2` into `x**2`. `[tool.ruff] extend-exclude = ["*.md"]` scopes that out. **Remove it only alongside a deliberate decision to format published content, never to make a red gate go green.** Keep the ruff version in step across all three places it is pinned: the `ruff-pre-commit` rev, the `ruff>=` floor in `pyproject.toml`, and whatever `uv.lock` resolves. They drifted to three different versions once, so local commits and CI ran different formatters.
- Pyright basic mode on `app/` only
- SQLite for development (`logic.db`, gitignored)
- **A gate that skips and a gate that passes render identically.** `ruff` reports `(no files to check) Skipped` on any commit staging no `.py`, and gitleaks in `--staged` mode always prints `0 commits scanned` — in that mode the honest signal is the **bytes** scanned, which read `~0 bytes` for the whole period the hook was silently broken. Never read a green hook as evidence the gate works; plant a canary and watch it go red. **Never add `args` to the gitleaks hook** — pre-commit appends them to the upstream `entry`, which is what broke it. Both halves of that are now asserted rather than commented: `tests/test_secret_gate_config.py` fails if the hook declares `args` at all, and the `staged-bytes-guard` hook makes an **empty** scan red instead of a green tick nobody can tell from a real pass. Neither proves gitleaks read the staged content — that still needs the canary. **Known cost of that hook:** an empty commit and a `git commit --amend` that changes only the message both leave the index equal to `HEAD`, and git gives a pre-commit hook no way to tell them apart, so both are blocked. Run those with the hooks off and say so in the message.
- Pre-commit hooks: gitleaks, opengrep, osv-scanner, ruff, pyright, pytest, standard hygiene checks. A `commit-msg`-stage hook (`scripts/check-airtable-ids.py`, id `airtable-id-guard`) additionally scans the commit *message*, which gitleaks cannot see. `default_install_hook_types` wires both stages on a plain `pre-commit install` — but **do not set `core.hooksPath`**: pre-commit refuses to install while it is set, so the message guard silently never arrives.
- **No local hook sees the message that actually lands on `main`.** This repository squash-merges, so the merge commit is composed in the GitHub web interface — as are web-editor commits, and any commit from a clone where `pre-commit install` was never run. The required `gitleaks` job therefore also runs `check-airtable-ids.py --pr-text` over the pull request's title, body and commit messages. It is a **step inside that job, not a job of its own**, because "Protect main" lists nine contexts by name and is managed outside this repository: a new job would be green-but-not-blocking until someone edited the ruleset by hand.
- **The identifier guard blocks on entropy OR structure, never on structure alone.** The 3.5 floor passes about one genuine identifier in thirty-eight, and the gitleaks rule shares the constant, so the blind spot is identical on both gates. Structural signals — a service URL in context, separator-only adjacency, three or more shape-matching tokens — close that tail on the Python side. They are added to the floor and must never replace it: a **lone** identifier satisfies no structural signal, and adjacency cannot be expressed in a gitleaks TOML rule, so replacing the floor would both pass the canonical leak and diverge the two gates.

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
- **A TypeScript port must match the Python core's rounding *mode*, not only its decimal places.** Python's `round()` is half-to-even; JavaScript's `Math.round` is half-away-from-zero, so `0.625` becomes `0.62` in one and `0.63` in the other. Scaling before rounding (`value * 100`) is also wrong — it manufactures ties the double does not have, so `51.585` rounds down when Python rounds it up. Use `site/src/lib/round.ts`, or its copy at `examples/remote-mcp/src/round.ts` — the two bodies are identical and must stay that way — and net any new port with fixtures generated from the core rather than reading the two implementations side by side; this divergence survived a line-by-line review because places and mode look alike. **A tolerance comparison does not hide this, but a thin case table does.** The example's twelve fixtures were green for a year against a port that rounded the wrong way, because none of them landed on a tie; the mode is now pinned directly by a shared table of rounding cases in both generators. Net the *displayed* value too — the site's tag panel computed its own multipliers and disagreed with the core by a penny on selections a visitor could reach, while every library-level test passed.

- **A build gate can only see the file you ship, not the one your CDN serves.** `site/public/robots.txt` was correct in this repository for months while production served something else entirely: Cloudflare's managed `robots.txt` setting was on, and it *prepends* its own block — disallowing `ClaudeBot`, `GPTBot`, `Google-Extended`, `CCBot`, `Applebot-Extended`, `meta-externalagent`, `Bytespider` and `Amazonbot` from the whole site. The live file was 1,903 bytes against the 60 in the tree. Nothing in the repository could see it, no grep matched any of those names, and no build could have caught it. `site/scripts/verify-crawlability.mjs` now checks that what we emit is internally coherent — every advertised sitemap resolves, every URL and `hreflang` alternate it lists was emitted, every emitted page is advertised, and nothing is disallowed — and it says plainly that this proves intent, never production. **If AI crawlers ever go quiet, `curl -s https://pmo.run/robots.txt` before you check the tree.** Same class as the dead gitleaks hook above: the configuration was right and inert.

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
