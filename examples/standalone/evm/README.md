# EVM (Earned Value Management)

**Performance metrics for project schedule and cost tracking in pure Python.**

Because "we're about 60% done" tells you nothing without knowing what you spent.

## The Problem

"Are we on track?"

This is the most common question in project management, and the most commonly lied about. Status reports say "green" until the week before the deadline, when everything turns red overnight. EVM eliminates the guesswork by connecting three numbers: what you planned, what you earned, and what you spent.

Four inputs. Ten metrics. One health signal. No opinions.

## Quick Start

```python
from evm import evm_metrics, health_signal, create_baseline, evaluate_progress, WorkPackage

# Direct calculation from raw values
result = evm_metrics(pv=100_000, ev=85_000, ac=95_000, bac=200_000)
print(f"SPI={result['spi']:.2f}  CPI={result['cpi']:.2f}")
# SPI=0.85  CPI=0.89 — behind schedule and over budget

signal = health_signal(result["spi"], result["cpi"])
print(f"Status: {signal['status']}")
# Status: off_track
```

## API

### `evm_metrics()` — The Atomic Calculation

```python
from evm import evm_metrics

result = evm_metrics(
    pv=100,    # Planned Value — budgeted cost of work scheduled
    ev=90,     # Earned Value — budgeted cost of work performed
    ac=110,    # Actual Cost — actual cost of work performed
    bac=500,   # Budget at Completion — total planned budget
)

# Returns:
# {
#     "sv": -10.0,           # Schedule Variance (EV - PV)
#     "spi": 0.9,            # Schedule Performance Index (EV / PV)
#     "cv": -20.0,           # Cost Variance (EV - AC)
#     "cpi": 0.8182,         # Cost Performance Index (EV / AC)
#     "eac": 611.11,         # Estimate at Completion (BAC / CPI)
#     "etc": 501.11,         # Estimate to Complete (EAC - AC)
#     "vac": -111.11,        # Variance at Completion (BAC - EAC)
#     "tcpi": 1.0513,        # To-Complete Performance Index
#     "percent_complete": 18.0,
#     "percent_spent": 22.0,
# }
```

**Dependencies:** None

### `health_signal()` — Actionable Status

```python
from evm import health_signal, HealthThresholds

# Default thresholds (PMI/PMBOK)
signal = health_signal(spi=0.85, cpi=1.05)
# {"status": "off_track", "reasons": [...], "summary": "..."}

# Custom thresholds for a strict startup
strict = HealthThresholds(
    spi_off_track=0.95, spi_at_risk=1.0,
    cpi_off_track=0.95, cpi_at_risk=1.0,
)
signal = health_signal(spi=0.92, cpi=0.97, thresholds=strict)
```

Three states: `on_track`, `at_risk`, `off_track`. Deliberately coarse — not five-colour traffic lights.

**Dependencies:** None

### `create_baseline()` — Freeze the Plan

```python
from evm import create_baseline, WorkPackage

baseline = create_baseline([
    WorkPackage("Requirements & Design", 3000),
    WorkPackage("Authentication Module", 5000),
    WorkPackage("API Development", 8000),
    WorkPackage("Frontend Integration", 7000),
    WorkPackage("Testing & QA", 4000),
    WorkPackage("Deployment & Docs", 3000),
])

print(f"BAC: ${baseline.bac:,.0f}")  # BAC: $30,000
# Weights are auto-normalised from planned values
```

**Dependencies:** None

### `evaluate_progress()` — Connect Baseline to Reality

```python
from evm import evaluate_progress

result = evaluate_progress(
    baseline=baseline,
    percent_planned=50.0,  # Month 3 of 6
    actual_completions=[
        {"name": "Requirements & Design", "percent_complete": 100.0},
        {"name": "Authentication Module", "percent_complete": 80.0},
        {"name": "API Development", "percent_complete": 30.0},
        {"name": "Frontend Integration", "percent_complete": 10.0},
        {"name": "Testing & QA", "percent_complete": 0.0},
        {"name": "Deployment & Docs", "percent_complete": 0.0},
    ],
    actual_cost=14500,
)

print(f"SPI={result['metrics']['spi']:.2f}")
print(f"Health: {result['health']['status']}")
# Per-work-package breakdown in result["work_packages"]
```

**Dependencies:** None

### `visualize_progress()` — Bar Chart

```python
from evm import visualize_progress

visualize_progress(result, save_path="evm_snapshot.png")
```

Bar chart showing PV, EV, AC against BAC with health status badge.

**Dependencies:** `matplotlib`

## EVM Terminology Cheat Sheet

### Inputs (what you provide)

| Abbr | Name | Meaning |
|------|------|---------|
| **BAC** | Budget at Completion | Total planned budget |
| **PV** | Planned Value | How much work *should* be done by now |
| **EV** | Earned Value | How much work *is* done (at planned rates) |
| **AC** | Actual Cost | What was actually spent |

### Core Metrics (computed)

| Abbr | Formula | Good When |
|------|---------|-----------|
| **SV** | EV - PV | >= 0 (ahead/on time) |
| **SPI** | EV / PV | >= 1.0 |
| **CV** | EV - AC | >= 0 (under/on budget) |
| **CPI** | EV / AC | >= 1.0 |

### Forecasts (computed)

| Abbr | Formula | Meaning |
|------|---------|---------|
| **EAC** | BAC / CPI | Projected total cost |
| **ETC** | EAC - AC | Remaining cost |
| **VAC** | BAC - EAC | Projected overrun |
| **TCPI** | (BAC-EV)/(BAC-AC) | Required CPI for remaining work |

**Memory aid:** "S" metrics compare EV to PV (schedule). "C" metrics compare EV to AC (cost). EV is always the left operand.

## The Mental Model

### Why TCPI Matters

TCPI is the hidden gem. If TCPI > 1.2, the remaining work needs superhuman cost efficiency — that's your re-baseline signal. Most PMOs ignore this metric; we highlight it.

### Why 3 Health States, Not 5

PMOs drown in traffic-light gradients where everything ends up amber. Three states force a binary: act or don't. The `HealthThresholds` dataclass lets each org calibrate what "off track" means to them.

### How EVM Connects to PERT

In the module family chain: `PERT -> Baseline -> EVM`

- PERT produces duration estimates per work package
- Those estimates become `planned_value` in the baseline (duration x cost rate)
- EVM tracks actual progress against that baseline

## Dependencies

| Function | Requires |
|----------|----------|
| `evm_metrics()` | Nothing |
| `health_signal()` | Nothing |
| `create_baseline()` | Nothing |
| `evaluate_progress()` | Nothing |
| `visualize_progress()` | matplotlib |

## Testing

```bash
# Run built-in demo
python evm.py
```

## License

MIT — Use it however you want.

---

**Philosophy:** Measure progress by value earned, not time spent.

*"In God we trust. All others must bring data."* — W. Edwards Deming
