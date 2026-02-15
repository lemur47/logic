# logic

**Atomic logic for decision-making.**
Turning abstract ideas into executable functions.

> Ship decisions, not spreadsheets.

A modular, privacy-first toolkit built with FastAPI and SQLAlchemy. Open source decision-making tools for the global PM/PMO community — every experiment, every formula, every line of code becomes a public deliverable.

## Philosophy

- **Executable:** Ideas are just hypotheses until they're code.
- **Composable:** Functions designed to be imported or piped.
- **Lean:** External dependencies are a last resort.
- **Privacy-first:** Your secrets stay local. Always.

## Modules

Every module follows: **Standalone PoC → FastAPI endpoint → Agent tool → Interactive UI**

| Module | Category | Status | Description |
|--------|----------|--------|-------------|
| TCO | Finance | ✅ Live | Total Cost of Ownership with NPV adjustment |
| PERT | P3M/P3G | 🔨 Next | Three-point estimation (optimistic/likely/pessimistic) |
| Base-rate | P3M/P3G | 📋 Planned | Reference class forecasting, reduce subjective bias |
| Bayesian | P3M/P3G | 📋 Planned | Bayesian updating for base-rate learning |
| NPV | Finance | 📋 Planned | Net Present Value analysis |
| IRR | Finance | 📋 Planned | Internal Rate of Return |

## Quick Start

```bash
git clone https://github.com/lemur47/logic.git && cd logic
uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload   # API at http://127.0.0.1:8000
```

## API Endpoints

```
GET    /                       API info
GET    /health                 Health check
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

## Architecture

Each feature module (e.g., `app/tco/`) follows a consistent layered pattern:

- **`core.py`** — Pure calculation functions. No FastAPI or DB dependencies. This is the atomic logic layer.
- **`router.py`** — FastAPI endpoints. Stateless endpoints call `core.py` directly; stateful endpoints go through `crud.py`.
- **`schemas.py`** — Pydantic models for request/response validation.
- **`models.py`** — SQLAlchemy ORM models.
- **`crud.py`** — Database operations. Calls `core.py` to compute values before persisting.

`examples/standalone/` contains self-contained library versions of modules (pure Python, optional pandas/matplotlib).

## Development

```bash
pytest                          # Run all tests
ruff check . && ruff format .   # Lint and format
pyright                         # Type check (app/ only)
bandit -c pyproject.toml -r .   # Security audit
pre-commit run --all-files      # Run all pre-commit hooks
```

Full commands, code style, and conventions are in [`CLAUDE.md`](CLAUDE.md).

## Docs

- [`CLAUDE.md`](CLAUDE.md) — Commands, architecture details, code style conventions
- [`docs/PMO_RUN_STRATEGY.md`](docs/PMO_RUN_STRATEGY.md) — Mission, roadmap, agent architecture, monetisation

## License

MIT
