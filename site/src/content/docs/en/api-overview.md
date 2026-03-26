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
| `calculate_breakeven()` | Find when a higher upfront cost pays off |

### PERT (Three-Point Estimation) — Live

| Function | Description |
|----------|-------------|
| `calculate_task()` | Single-task PERT with optional insight tags |
| `calculate_project()` | Multi-task project estimation with variance aggregation |

### EVM (Earned Value Management) — Live

| Function | Description |
|----------|-------------|
| `evm_metrics()` | Schedule and cost performance (SV, SPI, CV, CPI, EAC, TCPI) |
| `health_signal()` | Interpret metrics into actionable health status |
| `create_baseline()` | Create frozen project baseline from work packages |
| `evaluate_progress()` | Evaluate actual progress against baseline |

### Bayesian (Estimation Calibration) — Live

| Function | Description |
|----------|-------------|
| `update_belief()` | Compute posterior from prior belief and observed estimate-vs-actual pairs |
| `adjust_estimate()` | Apply a learned delay factor to a PERT estimate |

### Coming Soon

| Module | Category | Description |
|--------|----------|-------------|
| Monte Carlo | Simulation | Probabilistic schedule and cost simulation |
| Base-rate | Forecasting | Reference class forecasting to reduce subjective bias |
| NPV | Finance | Net Present Value analysis |
| IRR | Finance | Internal Rate of Return |

## Self-Host (Available Now)

Clone the repo and run locally:

```bash
git clone https://github.com/lemur47/logic.git && cd logic
uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload
```

API available at `http://127.0.0.1:8000`. Full endpoint docs at `/docs` (Swagger UI).

### TCO Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/tco/calculate` | Stateless TCO calculation |
| `POST` | `/tco/compare` | Compare options, ranked by annual cost |
| `POST` | `/tco/breakeven` | Break-even analysis between two options |
| `POST` | `/tco/scenarios` | Save a scenario |
| `GET` | `/tco/scenarios` | List scenarios (paginated, searchable) |
| `GET` | `/tco/scenarios/{id}` | Get a scenario |
| `PATCH` | `/tco/scenarios/{id}` | Update a scenario (auto-recalculates) |
| `DELETE` | `/tco/scenarios/{id}` | Delete a scenario |
| `GET` | `/tco/scenarios/stats` | Aggregate statistics |

### PERT Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/pert/task` | Single-task PERT estimate (with optional insight tags) |
| `POST` | `/pert/project` | Multi-task project estimation |

### EVM Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/evm/calculate` | Calculate EVM metrics (stateless) |
| `POST` | `/evm/health` | Health signal from SPI/CPI (stateless) |
| `POST` | `/evm/baselines` | Create a project baseline |
| `GET` | `/evm/baselines` | List baselines (paginated, searchable) |
| `GET` | `/evm/baselines/{id}` | Get a baseline with work packages |
| `DELETE` | `/evm/baselines/{id}` | Delete a baseline |
| `POST` | `/evm/baselines/{id}/evaluate` | Evaluate progress against baseline |
| `GET` | `/evm/baselines/{id}/snapshots` | List evaluation snapshots |

### Bayesian Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/bayesian/calculate` | Compute posterior from prior and observations (stateless) |
| `POST` | `/bayesian/adjust` | Apply delay factor to a PERT estimate (stateless) |
| `POST` | `/bayesian/contexts` | Create an estimation context |
| `GET` | `/bayesian/contexts` | List contexts (paginated, searchable) |
| `GET` | `/bayesian/contexts/{id}` | Get a context with current belief |
| `DELETE` | `/bayesian/contexts/{id}` | Delete a context and its observations |
| `POST` | `/bayesian/contexts/{id}/observations` | Add observations to a context |
| `GET` | `/bayesian/contexts/{id}/observations` | List observations (paginated) |
| `GET` | `/bayesian/contexts/{id}/belief` | Get current posterior belief |
| `POST` | `/bayesian/contexts/{id}/adjust` | Adjust a PERT estimate using context belief |

### Other Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | API info |
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

```python
from app.pert.core import calculate_task

result = calculate_task(optimistic=5, most_likely=8, pessimistic=15)
print(f"Expected: {result['textbook']['expected']:.1f} days")
```

```python
from app.evm.core import evm_metrics

result = evm_metrics(pv=100000, ev=85000, ac=95000, bac=200000)
print(f"SPI={result['spi']:.2f}  CPI={result['cpi']:.2f}")
```

```python
from app.bayesian.core import Prior, Observation, update_belief, adjust_estimate

prior = Prior(mean=1.0, variance=0.1)
observations = [Observation(estimated=5, actual=7), Observation(estimated=10, actual=13)]
posterior = update_belief(prior, observations)
result = adjust_estimate(pert_expected=8.0, posterior=posterior)
print(f"Adjusted: {result['adjusted_expected']:.1f} days")
```

## Hosted API

A hosted API at `api.pmo.run` is planned for Phase 2. It will include authentication, rate limits, and saved scenarios with encrypted storage.

For now, self-hosting is the way to go — and it's free, forever.

## Source

[github.com/lemur47/logic](https://github.com/lemur47/logic) — MIT License
