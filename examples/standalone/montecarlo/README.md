# Monte Carlo Schedule Simulation

Monte Carlo simulation generates a probability distribution over total project
duration by sampling thousands of schedules. Each task's duration is drawn from
a **beta-PERT distribution** — the same three-point estimates (optimistic, most
likely, pessimistic) used by textbook PERT.

## Why Monte Carlo Over PERT?

Textbook PERT gives you a single expected value and assumes the project duration
follows a normal distribution. This breaks down when:

- **Tasks have skewed estimates** — a task with O=4, M=7, P=16 has a long tail
  that PERT's Gaussian approximation underestimates.
- **Paths converge** — when parallel tasks merge at a dependency, the project
  takes the *longest* path. PERT sums variances assuming independence; Monte
  Carlo captures the merge effect directly.
- **You need actionable percentiles** — "P85 = 45 days" is a commitment you
  can defend. "Expected = 41 days" is not.

## Usage

```bash
python montecarlo.py
```

**Dependencies:** `numpy`, `scipy`. `matplotlib` optional for histogram
visualisation.

## API

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

# Read percentiles
print(result.percentiles)  # {'P50': ..., 'P75': ..., 'P85': ..., 'P95': ...}

# Probability of hitting a deadline
prob = probability_of_completion(result, target_duration=50.0)
print(f"Probability of finishing within 50 days: {prob:.1%}")

# Critical path frequency
print(result.critical_path_frequency)  # {'Design': 1.0, 'Build': 1.0, 'Test': 1.0}
```

## Worked Example: PERT vs Monte Carlo

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

## Test Scenarios

The script includes three self-verifying test scenarios:

1. **Beta-PERT distribution sampling** — verifies that 100,000 samples from
   PERT(O=2, M=5, P=14) produce a mean within 0.1 of the theoretical 6.0, and
   all samples stay within [O, P].

2. **Sequential schedule** — three independent tasks with no dependencies.
   Verifies MC mean matches PERT expected total (13.17) within 0.2, and all
   tasks show 100% critical path frequency.

3. **Dependency network** — A and B feed into C. Verifies C is always critical,
   both A and B appear on the critical path, and their frequencies sum to ~1.0
   (exactly one of A or B is critical in each simulation).

## Licence

MIT
