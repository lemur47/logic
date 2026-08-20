# logic

**Atomic logic for decision-making.**
Turning abstract ideas into executable functions.

> Ship decisions, not spreadsheets.

A modular toolkit built with FastAPI and SQLAlchemy. Open source decision-making tools for the global PM/PMO community — every experiment, every formula, every line of code becomes a public deliverable.

**The OSS is the free tier of value.** Full-strength tools — importable Python, Claude Skills, an MCP server ([`pmorun-mcp` on PyPI](https://pypi.org/project/pmorun-mcp/)) and open plugin interfaces — not a crippled trial. What sits behind a contract is the intelligence layer: analysis and insights, proprietary calibration plugins, and a managed data layer. The maths is never behind a paywall.

## Philosophy

- **Executable:** Ideas are just hypotheses until they're code.
- **Composable:** Functions designed to be imported or piped.
- **Lean:** External dependencies are a last resort.
- **Simple:** Fewer managed entities, more computed insights.
- **Privacy by design:** Explicit data zones with transparent boundaries.

## Modules

Every module follows: **Standalone PoC → FastAPI endpoint → Agent tool → Interactive UI**

**Finance** — "What will it cost and is it worth it?"

| Module | Status | Description |
|--------|--------|-------------|
| TCO | ✅ Live | Total Cost of Ownership with NPV adjustment |
| NPV | 📋 Planned | Net Present Value analysis |
| IRR | 📋 Planned | Internal Rate of Return |
| ROI | 📋 Planned | Return on Investment |

**Performance** — "How long will it take and are we on track?"

| Module | Status | Description |
|--------|--------|-------------|
| PERT | ✅ Live | Three-point estimation with reality adjustments |
| Monte Carlo | ✅ Live | Probabilistic schedule simulation (P50/P80/P95) |
| EVM | ✅ Live | Earned Value Management (SV, SPI, CV, CPI, EAC, TCPI) |
| Bayesian | ✅ Live | Bayesian estimation calibration from actuals |
| Base-rate | 📋 Planned | Reference class forecasting |

**Value Delivery** — "Are we delivering value?"

| Module | Status | Description |
|--------|--------|-------------|
| Flow Metrics | 📋 Planned | Cycle time, throughput, WIP analysis |

## Quick Start

```bash
git clone https://github.com/lemur47/logic.git && cd logic
# opengrep must be on PATH before the first commit — the pre-commit SAST hook
# shells out to it. gitleaks and osv-scanner do NOT need installing: their hooks
# build their own pinned copies. See CLAUDE.md for versions and binary sources.
uv venv
direnv allow
uv pip install -e ".[dev]"
pre-commit install
uv run uvicorn app.main:app --reload   # API at http://127.0.0.1:8000
```

## API Endpoints

### TCO

```
POST   /tco/calculate          Calculate TCO (stateless)
POST   /tco/compare            Compare options, ranked by annual cost
POST   /tco/breakeven          Break-even analysis between two options
POST   /tco/scenarios          Save a scenario
GET    /tco/scenarios          List scenarios (paginated, searchable)
GET    /tco/scenarios/{id}     Get a scenario
PATCH  /tco/scenarios/{id}     Update a scenario (auto-recalculates)
DELETE /tco/scenarios/{id}     Delete a scenario
GET    /tco/scenarios/stats    Aggregate statistics
```

### PERT

```
POST   /pert/task              Single-task PERT estimate (with optional insight tags)
POST   /pert/project           Multi-task project estimation
POST   /pert/scenarios         Save a scenario
GET    /pert/scenarios         List scenarios (paginated, searchable)
GET    /pert/scenarios/{id}    Get a scenario
PATCH  /pert/scenarios/{id}    Update a scenario (auto-recalculates)
DELETE /pert/scenarios/{id}    Delete a scenario
```

### Monte Carlo

```
POST   /montecarlo/simulate               Probabilistic schedule simulation (stateless)
POST   /montecarlo/simulate/target        Probability of completion within a target (stateless)
POST   /montecarlo/scenarios              Save a scenario
GET    /montecarlo/scenarios              List scenarios (paginated, searchable)
GET    /montecarlo/scenarios/stats        Aggregate statistics
GET    /montecarlo/scenarios/{id}         Get a scenario
PATCH  /montecarlo/scenarios/{id}         Update a scenario (auto-resimulates)
DELETE /montecarlo/scenarios/{id}         Delete a scenario
```

### EVM

```
POST   /evm/calculate                     Calculate EVM metrics (stateless)
POST   /evm/health                        Health signal from SPI/CPI (stateless)
POST   /evm/baselines                     Create a project baseline
GET    /evm/baselines                     List baselines (paginated, searchable)
GET    /evm/baselines/{id}                Get a baseline
DELETE /evm/baselines/{id}                Delete a baseline
POST   /evm/baselines/{id}/evaluate       Evaluate progress against baseline
GET    /evm/baselines/{id}/snapshots      List evaluation snapshots
```

### Bayesian

```
POST   /bayesian/calculate                      Compute posterior (stateless)
POST   /bayesian/adjust                         Apply delay factor to PERT estimate (stateless)
POST   /bayesian/contexts                       Create an estimation context
GET    /bayesian/contexts                       List contexts (paginated, searchable)
GET    /bayesian/contexts/{id}                  Get a context
DELETE /bayesian/contexts/{id}                  Delete a context
POST   /bayesian/contexts/{id}/observations     Add observations
GET    /bayesian/contexts/{id}/observations     List observations
GET    /bayesian/contexts/{id}/belief           Get current posterior belief
POST   /bayesian/contexts/{id}/adjust           Adjust PERT estimate using context belief
```

## Architecture

Each feature module (e.g., `app/tco/`) follows a consistent layered pattern:

- **`core.py`** — Pure calculation functions. No FastAPI or DB dependencies. This is the atomic logic layer.
- **`router.py`** — FastAPI endpoints. Stateless endpoints call `core.py` directly; stateful endpoints go through `crud.py`.
- **`schemas.py`** — Pydantic models for request/response validation.
- **`models.py`** — SQLAlchemy ORM models.
- **`crud.py`** — Database operations. Calls `core.py` to compute values before persisting.

`examples/standalone/` contains self-contained library versions of modules (pure Python, optional pandas/matplotlib):

```bash
python examples/standalone/tco/tco.py
python examples/standalone/pert/pert.py
python examples/standalone/montecarlo/montecarlo.py
python examples/standalone/evm/evm.py
python examples/standalone/bayesian/bayesian.py
```

## Development

```bash
pytest                          # Run all tests
ruff check . && ruff format .   # Lint and format
pyright                         # Type check (app/ only)
opengrep scan --config .opengrep/  # Security audit (SAST)
pre-commit run --all-files      # Run all pre-commit hooks
```

Full commands, code style, and conventions are in [`CLAUDE.md`](CLAUDE.md).

## MCP Server

The decision modules ship as a lean stdio MCP server — runs locally, no account, no data leaves your machine:

```bash
uvx pmorun-mcp                                # run the published server
claude mcp add pmo-logic -- uvx pmorun-mcp    # or one line into Claude Code
```

Four tools over stdio by default: task duration estimation (PERT), schedule risk (Monte Carlo), investment comparison (TCO) and project health (EVM).

Set `PMORUN_DB` to a writable file path and four more register — an opt-in **calibration memory** that records what you estimated, then what actually happened, and learns your systematic bias from the pairs. Leave the variable unset and the server writes nothing at all. See [`mcp_server/README.md`](mcp_server/README.md) for pinning, client configuration, and the storage caveats.

## Claude Skills

Same logic, conversational interface. Add a `SKILL.md` to a [Claude Project](https://claude.ai) and start estimating — no deployment needed.

| Skill | Description |
|-------|-------------|
| [TCO](skills/tco/SKILL.md) | Total Cost of Ownership with NPV adjustment |
| [PERT](skills/pert/SKILL.md) | Three-point estimation with reality adjustments |
| [Monte Carlo](skills/montecarlo/SKILL.md) | Probabilistic schedule simulation (P50/P80/P95) |
| [EVM](skills/evm/SKILL.md) | Earned Value Management for project health tracking |

See [`skills/README.md`](skills/README.md) for details.

Alongside these, [`skills/operational/`](skills/operational/README.md) holds a
different class — guardrails on *how the work is done* rather than decision
maths, with organisation specifics kept in gitignored overlays. Most of that set
(session rituals, staleness sweeps, a ship loop, an anonymisation gate) now lives
in **[agent-ops](https://github.com/lemur47/agent-ops)**, since it governs how an
agent works rather than anything about this repository; `content-cadence` remains
here.

## Repository Automation

[`automation/`](automation/) holds automation that acts on this repository rather
than shipping as product. Today that is one thing: a **PR auditor** that reviews
every pull request unattended and posts a single comment. It cannot approve,
merge, label or block, and it is not a required check — the token behind it is
scoped to commenting. Contributors should expect a comment and read it as one
reviewer's opinion.

The design, the reviewer's system prompt and the exported scenario are all in
[`automation/pr-auditor/`](automation/pr-auditor/README.md), because a review
prompt is a security control and reviewing it in a pull request is the point.

## Docs

- [`CLAUDE.md`](CLAUDE.md) — Commands, architecture details, code style conventions
- [`docs/STRATEGY.md`](docs/STRATEGY.md) — Mission, audiences, monetisation, IP strategy, competitive positioning
- [`docs/DESIGN.md`](docs/DESIGN.md) — Six-layer architecture, agent design, three-zone privacy model, technical decisions
- [`docs/SPRINT_HISTORY.md`](docs/SPRINT_HISTORY.md) — Sprint actuals
- [`docs/CONTENT_FLYWHEEL.md`](docs/CONTENT_FLYWHEEL.md) — R&D → blog → community → consulting loop

## License

MIT
