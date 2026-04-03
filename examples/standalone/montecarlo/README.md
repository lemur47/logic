# Monte Carlo Schedule Simulation

**Probability distributions over project duration in pure Python.**

Because "expected value" is not a commitment.

## The Problem

"PERT says 41 days. Let's commit to that."

Six weeks later, the project is at day 48. Nobody is surprised — except the stakeholder who trusted the single-point estimate.

Textbook PERT gives you an expected value and a Gaussian confidence band. That breaks down when:

- **Tasks have skewed estimates** — a task with O=4, M=7, P=16 has a long tail that PERT's Gaussian approximation underestimates
- **Paths converge** — when parallel tasks merge at a dependency, the project takes the *longest* path. PERT sums variances assuming independence; Monte Carlo captures the merge effect directly
- **You need actionable percentiles** — "P85 = 45 days" is a commitment you can defend. "Expected = 41 days" is not

Monte Carlo replaces the single point with a full distribution. Run 10,000 simulated schedules, get percentiles, critical path frequencies, and target-date probabilities.

## Quick Start

```python
from montecarlo import Task, simulate_schedule, probability_of_completion

# Define tasks with three-point estimates
tasks = [
    Task("Design", 4, 7, 12),
    Task("Build", 8, 14, 25, depends_on=("Design",)),
    Task("Test", 4, 7, 14, depends_on=("Build",)),
]

# Run simulation
result = simulate_schedule(tasks, n_simulations=10_000, seed=42)

print(result.percentiles)
# {'P50': ..., 'P75': ..., 'P85': ..., 'P95': ...}

prob = probability_of_completion(result, target_duration=50.0)
print(f"Probability of finishing within 50 days: {prob:.1%}")
```

## API

### `simulate_schedule()` — The Core

```python
from montecarlo import Task, simulate_schedule

tasks = [
    Task("Design", 4, 7, 12),
    Task("Build", 8, 14, 25, depends_on=("Design",)),
    Task("Test", 4, 7, 14, depends_on=("Build",)),
]

result = simulate_schedule(tasks, n_simulations=10_000, seed=42)

# Returns SimulationResult with:
# - result.durations         # numpy array of project durations
# - result.percentiles       # {'P50': ..., 'P75': ..., 'P85': ..., 'P95': ...}
# - result.histogram         # {'bin_edges': [...], 'counts': [...]}
# - result.critical_path_frequency  # {'Design': 1.0, 'Build': 0.85, ...}
```

**Dependencies:** `numpy`, `scipy`

### `probability_of_completion()` — Target Date Query

```python
from montecarlo import probability_of_completion

prob = probability_of_completion(result, target_duration=50.0)
print(f"Probability of finishing within 50 days: {prob:.1%}")
```

**Dependencies:** `numpy`

### `compare_with_pert()` — Side-by-Side

```python
from montecarlo import compare_with_pert

comparison = compare_with_pert(tasks)
print(comparison["pert"]["expected"])       # PERT expected total
print(comparison["montecarlo"]["mean"])     # MC mean
print(comparison["montecarlo"]["percentiles"])  # P50, P75, P85, P95
```

**Dependencies:** `numpy`, `scipy`

### `visualise_distribution()` — Histogram Chart

```python
from montecarlo import visualise_distribution

fig = visualise_distribution(result, target_duration=50.0, save_path="histogram.png")
```

Histogram with percentile lines (P50, P75, P85, P95) and optional target deadline overlay.

**Dependencies:** `matplotlib`

## Real-World Applications

### Sprint Commitment

```python
sprint_tasks = [
    Task("Auth refactor", 3, 5, 12),
    Task("Dashboard UI", 4, 7, 14, depends_on=("Auth refactor",)),
    Task("API integration", 2, 4, 10, depends_on=("Auth refactor",)),
    Task("Testing", 3, 5, 8, depends_on=("Dashboard UI", "API integration")),
]

result = simulate_schedule(sprint_tasks, seed=42)
# Commit to P85, not the expected value
print(f"Commit to: {result.percentiles['P85']:.0f} days")
```

### Vendor Timeline Validation

When a vendor says "6–8 weeks":

```python
vendor_tasks = [
    Task("Phase 1", 4, 6, 8),
    Task("Phase 2", 3, 5, 10, depends_on=("Phase 1",)),
    Task("Delivery", 2, 3, 6, depends_on=("Phase 2",)),
]

result = simulate_schedule(vendor_tasks, seed=42)
prob = probability_of_completion(result, target_duration=56.0)  # 8 weeks in days
# Now you know the real probability of their "8 weeks" promise
```

### Risk Comparison

```python
# Symmetric tasks: predictable
symmetric = [Task("A", 4, 7, 10), Task("B", 3, 6, 9)]

# Skewed tasks: same mode, much wider tail
skewed = [Task("A", 4, 7, 16), Task("B", 3, 6, 15)]

sym_result = simulate_schedule(symmetric, seed=42)
skew_result = simulate_schedule(skewed, seed=42)
# Compare P95 — the skewed tasks carry far more schedule risk
```

## Worked Example

A six-task software project with dependencies:

```
Requirements → Design → Backend  ─┐
                      → Frontend ─┤→ Integration → Testing
```

### Input

| Task         | Optimistic | Most Likely | Pessimistic | Depends On              |
|--------------|-----------|-------------|-------------|-------------------------|
| Requirements | 3         | 5           | 10          | —                       |
| Design       | 4         | 7           | 12          | Requirements            |
| Backend      | 8         | 14          | 25          | Design                  |
| Frontend     | 6         | 10          | 18          | Design                  |
| Integration  | 3         | 5           | 10          | Backend, Frontend       |
| Testing      | 4         | 7           | 14          | Integration             |

### Output (actual, seed=42)

```
                             PERT   Monte Carlo
  ──────────────────────────────────────────────
  Expected/Mean             51.50         41.08
  Std dev                    4.39          4.16
  P50                           —         40.94
  P75                           —         43.94
  P85                           —         45.48
  P95                           —         48.08
```

Key insight: **PERT overestimates by ~10 days** because it sums all six tasks'
expected values as if they were sequential. Monte Carlo respects the dependency
network and only sums tasks along the critical path.

### Critical Path Frequency

```
  Requirements         100.0%  ##############################
  Design               100.0%  ##############################
  Backend               85.4%  #########################
  Frontend              14.6%  ####
  Integration          100.0%  ##############################
  Testing              100.0%  ##############################
```

Backend dominates Frontend on the critical path (85% vs 15%), but Frontend is
not negligible — in ~15% of simulations, Frontend delays the project. This
is information that deterministic critical path analysis cannot provide.

### Target Date Analysis

```
  Complete within 45 days: 82.2%
  Complete within 50 days: 98.2%
  Complete within 55 days: 99.9%
```

If the stakeholder asks "can we ship in 45 days?", the answer is "82% likely —
commit to 50 days for 98% confidence."

## The Mental Model

### Why Single-Point Estimates Fail

PERT's formula — `(O + 4M + P) / 6` — is solid maths on a flawed assumption: that project duration follows a normal distribution.

In practice:

1. **Skewed tails are invisible** — A task with O=4, M=7, P=16 has a right tail that the Gaussian approximation clips. Monte Carlo samples from the actual beta-PERT distribution, preserving the skew.
2. **Path convergence eats your buffer** — When parallel tasks merge, the project takes the *longest* path. With 10,000 simulations, you see exactly how often each path dominates.
3. **Percentiles beat expected values** — Nobody ships at the expected value. P85 tells you "85% of simulated schedules finished by this date." That is a defensible commitment.

### Critical Path Frequency

Deterministic CPM identifies *one* critical path. Monte Carlo shows that the critical path *changes across simulations* as task durations vary. A task that is critical 15% of the time still needs attention — it is a latent risk that deterministic analysis misses entirely.

## Dependencies

| Function | Requires |
|----------|----------|
| `simulate_schedule()` | numpy, scipy |
| `probability_of_completion()` | numpy |
| `compare_with_pert()` | numpy, scipy |
| `visualise_distribution()` | matplotlib |

## Testing

```bash
# Run built-in examples
python montecarlo.py

# Run test suite
pytest test_montecarlo.py -v
```

## Licence

MIT — Use it however you want.

---

**Philosophy:** Make uncertainty visible, then commit with confidence.

*"Prediction is very difficult, especially about the future."* — Niels Bohr
