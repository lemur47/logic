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

## Dirichlet-Drift Extension

**`dirichlet_drift.py` — Bayesian-calibrated drift on top of plain Monte Carlo.**

Plain Monte Carlo assumes your three-point estimates are unbiased. They rarely are. If past auth tasks have run 15% over, that bias should propagate into the next auth task's percentiles — not be re-discovered by every project.

The drift extension layers a per-task multiplier `d_j` on top of the beta-PERT-sampled duration. The multiplier comes from caller-supplied Bayesian posteriors per **risk class** (e.g. "auth", "infra"), combined with **Dirichlet weights** that express uncertainty over the class-mix for tasks you haven't classified.

Per simulation iteration:

1. Sample beta-PERT duration `D_j` for each task.
2. Sample posterior delay factor `mu_k ~ N(mu_k, sigma_k)` for each risk class `k`.
3. Sample Dirichlet class-mix weights `w ~ Dir(alpha_1, ..., alpha_K)`.
4. For each task: `d_j = mu_{class(j)}` if classified, else `d_j = sum_k w_k * mu_k`.
5. Apply: `D'_j = d_j * D_j`. Run the standard forward pass on `D'`.

Caller-supplied posteriors — this module does **not** import the Bayesian module. Risk classes without an explicit posterior fall back to an uninformative `N(1.0, 0.5)` prior.

### Quick Start

```python
from dirichlet_drift import (
    DriftConfig, DriftTask, Posterior, RiskClass, simulate_with_drift,
)

tasks = [
    DriftTask("Auth API", 4, 7, 14, risk_class="auth"),
    DriftTask("Infra setup", 5, 8, 18, risk_class="infra"),
    DriftTask("Discovery", 3, 5, 10),  # unclassified — Dirichlet-blended
]
config = DriftConfig(
    risk_classes=(
        RiskClass("auth", posterior=Posterior(mu=1.15, sigma=0.10)),
        RiskClass("infra", posterior=Posterior(mu=1.05, sigma=0.30)),
    ),
    seed=42,
)

result = simulate_with_drift(tasks, config, n_simulations=20_000)
print(result.percentiles)
print(result.class_contribution)
```

### Worked Example

A six-task project with two risk classes (`auth` and `infra`) and one unclassified task (`Discovery`). Calibration: auth runs ~15% over (sigma 0.10 — we have data); infra runs ~5% over (sigma 0.30 — we have less).

```
Discovery → Auth API ─┐
          → Auth UI  ─├→ Integration → Hardening
          → Infra    ─┘
```

| Task          | O | M | P  | Risk class | Depends on                        |
|---------------|---|---|----|------------|-----------------------------------|
| Discovery     | 3 | 5 | 10 | —          | —                                 |
| Auth API      | 4 | 7 | 14 | auth       | Discovery                         |
| Auth UI       | 3 | 5 | 10 | auth       | Discovery                         |
| Infra setup   | 5 | 8 | 18 | infra      | Discovery                         |
| Integration   | 3 | 5 | 10 | infra      | Auth API, Auth UI, Infra setup    |
| Hardening     | 2 | 4 | 8  | —          | Integration                       |

#### Output (actual, seed=42, 20 000 simulations)

```
                       Plain MC    Drift MC
  ────────────────────────────────────────
  Mean                    25.08       27.65
  Std dev                  2.89        6.02
  P50                     24.97       27.12
  P75                     26.99       31.28
  P85                     28.14       33.71
  P95                     30.00       38.34
```

**Class contribution diagnostics:**

```
  auth   weight=0.502  mu=1.150  tasks_bound=2
  infra  weight=0.498  mu=1.054  tasks_bound=2
```

Drift adds ~10% to the mean and ~28% to P85. Most of the spread widening comes from `infra`'s diffuse posterior (sigma 0.30) propagating through the longer-tailed Infra setup task — visible as the much wider gap between Drift P50 and P95.

This is the value: deterministic CPM and plain MC both miss this. The drift extension carries forward what you've learned about systematic bias — and exposes how much of your remaining uncertainty is calibration risk versus task-level risk.

### API Reference

| Type             | Purpose                                                                                                  |
|------------------|----------------------------------------------------------------------------------------------------------|
| `Posterior`      | Gaussian posterior on a class delay factor. Validates `mu >= 0`, `sigma >= 0`.                           |
| `RiskClass`      | Named class with a Dirichlet `prior_alpha` and optional `posterior`. Falls back to `N(1.0, 0.5)`.        |
| `DriftTask`      | Subclass of `Task` with an optional `risk_class: str`.                                                   |
| `DriftConfig`    | Tuple of `RiskClass` plus `seed`. Validates non-empty and unique class names.                            |
| `DriftResult`    | Mirrors `SimulationResult` and adds `class_contribution` and `dirichlet_weights_used`.                   |

### Verification

`python dirichlet_drift.py` runs six self-checks:

1. **Degenerate reducibility** — drift with neutral posteriors matches plain MC within statistical tolerance (~0.01% on the test schedule).
2. **Mean shift** — posterior `mu = 1.3` shifts the mean by exactly 30%.
3. **Variance propagation** — diffuse posterior (`sigma 0.4`) widens the spread by ~2.8× vs sharp posterior.
4. **Dirichlet blending** — uniform-alpha blend of `mu = {1.0, 2.0}` gives expected drift 1.5; actual matches within 2%.
5. **Re-estimation monotonicity** — narrowing posterior sigma never widens the result spread.
6. **Cross-project carry-forward** — `prior_new = posterior_old` with the same seed gives bit-identical durations (no hidden state).

The full pytest suite (`test_dirichlet_drift.py`) covers these plus validation of malformed inputs.

## Testing

```bash
# Run built-in examples
python montecarlo.py
python dirichlet_drift.py

# Run test suites
pytest test_montecarlo.py -v
pytest test_dirichlet_drift.py -v
```

## Licence

MIT — Use it however you want.

---

**Philosophy:** Make uncertainty visible, then commit with confidence.

*"Prediction is very difficult, especially about the future."* — Niels Bohr
