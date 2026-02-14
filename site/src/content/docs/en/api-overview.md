---
title: "Logic API"
description: "Open source decision-making modules — self-host or use via Python. Hosted API coming soon."
order: 1
---

## What is the Logic API?

The logic repo provides composable decision-making modules as pure Python functions and FastAPI endpoints. Every module is open source, stateless by default, and designed to be imported into your own systems.

## Available Modules

### TCO (Total Cost of Ownership) — Live

| Function | Description |
|----------|-------------|
| `calculate_tco()` | Compute total and annual cost with NPV adjustment |
| `compare_options()` | Rank multiple options by annual cost |
| `breakeven_analysis()` | Find when a higher upfront cost pays off |

### Coming Soon

| Module | Category | Description |
|--------|----------|-------------|
| PERT | Estimation | Three-point estimation (optimistic / likely / pessimistic) |
| Base-rate | Forecasting | Reference class forecasting to reduce subjective bias |
| NPV | Finance | Net Present Value analysis |

## Self-Host (Available Now)

Clone the repo and run locally:

```bash
git clone https://github.com/lemur47/logic.git && cd logic
uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload
```

API available at `http://127.0.0.1:8000`. Full endpoint docs at `/docs` (Swagger UI).

### Endpoints (Self-Hosted)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/tco/calculate` | Stateless TCO calculation |
| `POST` | `/tco/compare` | Compare options, ranked by annual cost |
| `POST` | `/tco/breakeven` | Break-even analysis between two options |
| `POST` | `/tco/scenarios` | Save a scenario |
| `GET` | `/tco/scenarios` | List scenarios (paginated, searchable) |
| `GET` | `/tco/scenarios/stats` | Aggregate statistics |
| `GET` | `/health` | Health check |

### Python Import

You can also use the logic directly without the API:

```python
from app.tco.core import calculate_tco

result = calculate_tco(
    initial_price=450000,
    useful_life_years=12,
    residual_value=90000,
    annual_maintenance=5000,
)
print(f"Annual cost: {result['annual_cost']:,.0f}")
```

## Hosted API

A hosted API at `api.pmo.run` is planned for Phase 2. It will include authentication, rate limits, and saved scenarios with encrypted storage.

For now, self-hosting is the way to go — and it's free, forever.

## Source

[github.com/lemur47/logic](https://github.com/lemur47/logic) — MIT License
