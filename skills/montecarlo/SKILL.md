# Monte Carlo: Schedule Simulation with Probability Distributions

> Source: [github.com/lemur47/logic](https://github.com/lemur47/logic)

## Purpose

Help users answer one question: **"What's the probability we finish by this date?"** using Monte Carlo schedule simulation. This skill replaces single-point PERT estimates with full probability distributions over project duration.

Monte Carlo builds on PERT. PERT asks "how long will it take?" and gives a single expected value. Monte Carlo takes the same three-point estimates, runs thousands of simulated schedules, and returns percentiles, critical path frequencies, and target-date probabilities. The expected value becomes a distribution.

## When to Use

- Sprint or project commitment decisions ("should we commit to 40 days?")
- Comparing PERT expected value against realistic percentile-based commitments
- Identifying which tasks drive schedule risk via critical path frequency
- Target-date probability queries ("what's the chance we ship by April 15?")
- Any situation where a stakeholder needs a confidence level, not a point estimate

## When NOT to Use

- Single-task estimation with no dependencies — use the PERT Skill directly
- You need reality adjustments via insight tags — use PERT first, then feed the adjusted estimates into Monte Carlo
- You need Dirichlet drift or time-evolving simulation — out of scope (Sprint 7)

## Core Concepts

### Beta-PERT Distribution

Each task's duration is sampled from a beta-PERT distribution, parameterised by the same three-point estimates used by textbook PERT:

- **O** — Optimistic (best case)
- **M** — Most likely (realistic)
- **P** — Pessimistic (worst case)

The beta-PERT distribution is a beta distribution rescaled to [O, P] with the mode at M. Unlike PERT's Gaussian approximation, it preserves the skew in asymmetric estimates.

### Simulation Process

For each of N simulations (default 10,000):

1. Sample a random duration for every task from its beta-PERT distribution
2. Compute task start and finish times respecting dependency constraints (forward pass)
3. Record the total project duration (max finish time)
4. Identify which tasks are on the critical path (zero total float)

The result is an empirical distribution of project durations.

### Percentiles

```
P50  — 50% of simulations finish by this date (median)
P75  — 75% finish by this date
P85  — 85% finish by this date (recommended commitment level)
P95  — 95% finish by this date (conservative buffer)
```

**P85 is the recommended commitment level.** It balances confidence against over-padding. P50 is a coin flip. P95 is a safety blanket.

### Critical Path Frequency

Deterministic CPM gives you one critical path. Monte Carlo shows that the critical path *changes across simulations* as durations vary. A task that is critical in 15% of simulations is a latent risk that deterministic analysis misses.

For sequential schedules (no dependencies), every task is always on the critical path (100%).

## Execution Instructions

### Step 1: Collect Task Inputs

For each task, gather:

1. **Name** — human-readable identifier
2. **Optimistic (O)** — best-case duration, must be ≥ 0
3. **Most likely (M)** — most probable duration, must be ≥ O
4. **Pessimistic (P)** — worst-case duration, must be ≥ M
5. **Dependencies** — which tasks must complete before this one starts (optional)

Validate: O ≤ M ≤ P for every task. If dependencies form a cycle, flag the error.

### Step 2: Calculate PERT Baseline

For context, compute the textbook PERT expected total:

```
PERT expected = Σ (O + 4M + P) / 6   for each task
PERT std dev  = √(Σ ((P - O) / 6)²)
```

Note: PERT sums all tasks as if they were sequential. If the project has parallel paths, the PERT total will overestimate because it doesn't account for path convergence.

### Step 3: Run Monte Carlo Simulation

Simulate with seed=42 for reproducibility (unless the user specifies otherwise). Use n_simulations=10,000 for standard accuracy.

```python
from app.montecarlo.core import Task, simulate_schedule

tasks = [
    Task("name", optimistic, most_likely, pessimistic, depends_on=("dep1",)),
    ...
]
result = simulate_schedule(tasks, n_simulations=10_000, seed=42)
```

Or via the API:

```
POST /montecarlo/simulate
{
    "tasks": [
        {"name": "...", "optimistic": O, "most_likely": M, "pessimistic": P, "depends_on": ["..."]}
    ],
    "config": {"num_simulations": 10000, "seed": 42}
}
```

### Step 4: Present Results

Show PERT vs Monte Carlo side by side:

```
                        PERT        Monte Carlo
Expected/Mean:          X days      Y days
Std dev:                A           B
P50:                    —           Z days
P75:                    —           Z days
P85:                    —           Z days  ← recommended commitment
P95:                    —           Z days
```

Highlight the gap between PERT expected and MC P85 — this is the schedule risk that single-point estimation hides.

### Step 5: Critical Path Analysis

Present which tasks drive schedule risk:

```
Task              Critical Frequency
Requirements      100.0%
Design            100.0%
Backend            85.4%
Frontend           14.6%
Testing           100.0%
```

Explain: tasks at 100% are always on the critical path. Tasks below 100% are sometimes critical — they represent latent risk. If two parallel tasks feed into a merge point, their frequencies should sum to approximately 100%.

### Step 6: Target Date Queries

If the user has a deadline, compute the probability of meeting it:

```
Complete within 35 days: 66.5%
Complete within 40 days: 95.5%
Complete within 45 days: 100.0%
```

Frame the answer as: "There is a X% chance the project finishes within Y days. For Z% confidence, commit to W days."

## Worked Examples (Self-Check)

### Worked Example A — Five-Task Project with Dependencies

**Tasks:**

| Task         | O  | M  | P  | Depends On              |
|--------------|----|----|-----|-------------------------|
| Requirements | 3  | 5  | 10  | —                       |
| Design       | 4  | 7  | 12  | Requirements            |
| Backend      | 8  | 14 | 25  | Design                  |
| Frontend     | 6  | 10 | 18  | Design                  |
| Testing      | 3  | 5  | 10  | Backend, Frontend       |

**Network:**
```
Requirements → Design → Backend  ─┐
                      → Frontend ─┤→ Testing
```

**PERT baseline:**
```
PERT expected (sum of all tasks) = 43.83 days
PERT std dev = 4.06
PERT 68% range = [39.77, 47.90]
PERT 95% range = [35.70, 51.96]
```

Note: PERT sums all five tasks as if sequential. But Backend and Frontend run in parallel, so the true project duration is shorter.

**Monte Carlo results (seed=42, 10,000 simulations):**
```
MC mean:    33.42 days
MC std dev:  3.76
P50:        33.26 days
P75:        36.02 days
P85:        37.48 days  ← commit to this
P95:        39.82 days
```

**Gap:** PERT overestimates by ~10 days (43.83 vs 33.42) because it doesn't account for the parallel Backend/Frontend paths. Monte Carlo captures the path convergence.

**Critical path frequency:**
```
Requirements:  100.0%
Design:        100.0%
Backend:        85.4%
Frontend:       14.6%
Testing:       100.0%
```

Backend dominates Frontend (85% vs 15%), but Frontend is not negligible — in ~15% of simulations, Frontend delays the project.

**Target date analysis:**
```
Complete within 35 days: 66.5%
Complete within 40 days: 95.5%
Complete within 45 days: 100.0%
```

**Recommendation:** Commit to 38 days (P85). PERT's 44-day estimate includes ~10 days of phantom duration from double-counting the parallel path.

### Worked Example B — Sequential Tasks (No Dependencies)

**Tasks:**

| Task | O | M | P |
|------|---|---|---|
| A    | 2 | 4 | 8 |
| B    | 3 | 5 | 10|
| C    | 1 | 3 | 7 |

No dependencies — tasks are sequential.

**PERT expected:** (4.33 + 5.50 + 3.33) = 13.17 days

**Monte Carlo (seed=42, 50,000 simulations):**
- MC mean ≈ 13.17 (matches PERT — correct for sequential, no convergence effect)
- All tasks at 100% critical path frequency

**Key insight:** When there are no parallel paths, Monte Carlo and PERT agree on the mean. Monte Carlo's value here is the *distribution* — you get P85 and P95, not just the expected value.

Use these examples to verify your calculations are correct before presenting results to the user.

## What This Skill Does NOT Cover

- **PERT estimation with insight tags** — for reality-adjusted three-point estimates, use the PERT Skill first. You can then feed the adjusted estimates into Monte Carlo.
- **Dirichlet drift** — time-evolving simulation with Bayesian-updated drift coefficients. Planned for Sprint 7.
- **Scenario persistence** — saving and comparing simulation scenarios over time. Use the API for CRUD operations.
- **EVM tracking** — for monitoring actuals against baselines, use the EVM Skill.
- **TCO analysis** — for cost comparisons, use the TCO Skill.

For programmatic access, scenario persistence, or batch simulations, point to the API at [github.com/lemur47/logic](https://github.com/lemur47/logic).

## Tone

Be direct and practical. Present percentiles as commitments, not hedging. When a user asks "how long will this take?" — give them P85, explain what it means, and show them the PERT gap. The point of Monte Carlo is to make uncertainty visible and actionable. Don't over-explain the statistics; focus on what the numbers mean for the decision.
