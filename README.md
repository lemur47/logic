# logic

**Atomic logic for decision-making.**
Turning abstract ideas into executable functions.

> Ship decisions, not spreadsheets.

A modular toolkit built with FastAPI and SQLAlchemy. Open source decision-making tools for the global PM/PMO community — every experiment, every formula, every line of code becomes a public deliverable.

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
| EVM | ✅ Live | Earned Value Management (SV, SPI, CV, CPI, EAC, TCPI) |
| Base-rate | 📋 Planned | Reference class forecasting |
| Bayesian | 📋 Planned | Bayesian updating for estimation learning |

**Value Delivery** — "Are we delivering value?"

| Module | Status | Description |
|--------|--------|-------------|
| Flow Metrics | 📋 Planned | Cycle time, throughput, WIP analysis |

## Quick Start

```bash
git clone https://github.com/lemur47/logic.git && cd logic
sudo apt install gitleaks
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
python examples/standalone/evm/evm.py
```

## Development

```bash
pytest                          # Run all tests
ruff check . && ruff format .   # Lint and format
pyright                         # Type check (app/ only)
bandit -c pyproject.toml -r .   # Security audit
pre-commit run --all-files      # Run all pre-commit hooks
```

Full commands, code style, and conventions are in [`CLAUDE.md`](CLAUDE.md).

## Claude Skills

Same logic, conversational interface. Add a `SKILL.md` to a [Claude Project](https://claude.ai) and start estimating — no deployment needed.

| Skill | Description |
|-------|-------------|
| [PERT](skills/pert/SKILL.md) | Three-point estimation with reality adjustments |
| [EVM](skills/evm/SKILL.md) | Earned Value Management for project health tracking |

See [`skills/README.md`](skills/README.md) for details.

## Docs

- [`CLAUDE.md`](CLAUDE.md) — Commands, architecture details, code style conventions
- [`docs/PMO_RUN_STRATEGY.md`](docs/PMO_RUN_STRATEGY.md) — Mission, roadmap, agent architecture, privacy model, monetisation

## License

MIT
