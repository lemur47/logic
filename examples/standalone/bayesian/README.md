# Bayesian Estimation Calibration

**Learn systematic estimation bias from observed data, then correct for it.**

Because "we always underestimate auth tasks" should be a number, not a feeling.

## The Problem

Your team estimates a task at 10 days. It takes 13. Next sprint, similar task: estimated 8 days, takes 10. The pattern is obvious to anyone who's been paying attention — but PERT doesn't learn. Every new estimate starts from scratch.

This module learns. It takes (estimated, actual) duration pairs and uses Bayesian updating to compute a **delay factor** — a calibrated multiplier that tells you how much to adjust future estimates. Different task categories (auth, infra, frontend) get their own delay factors, because estimation bias isn't uniform.

The maths is conjugate normal-normal inference — the same framework used in the Stanford FOMC dual-track model for policy rate beliefs. No LLMs, no black boxes. Deterministic, sequential, and auditable.

## Quick Start

```python
from bayesian import Prior, Observation, update_belief, adjust_estimate

# Start with an uninformative prior: "estimates are roughly right"
prior = Prior(mean=1.0, variance=0.25)

# Feed in historical observations
observations = [
    Observation(estimated=5, actual=7, context="auth"),    # r = 1.40
    Observation(estimated=10, actual=13, context="auth"),  # r = 1.30
    Observation(estimated=8, actual=10, context="auth"),   # r = 1.25
]

posterior = update_belief(prior, observations)
print(f"Delay factor: {posterior.mean:.3f}")  # ~1.31
# Auth tasks take ~31% longer than estimated

# Apply to a new PERT estimate
result = adjust_estimate(12.0, posterior)
print(f"Adjusted: {result['adjusted_expected']} days")  # ~15.7 days
print(f"95% range: {result['adjusted_range_95']}")
```

## API

### `update_belief()` — Stateless Bayesian Update

```python
from bayesian import Prior, Observation, update_belief

posterior = update_belief(
    prior=Prior(mean=1.0, variance=0.25),  # Gaussian prior on delay factor
    observations=[...],                     # List of (estimated, actual) pairs
    observation_noise=0.15,                 # Assumed scatter in observations
)

# Returns Posterior with:
#   mean          — calibrated delay factor
#   variance      — remaining uncertainty
#   std_dev       — √variance
#   n_observations
#   credible_interval_68  — ±1σ
#   credible_interval_95  — ±1.96σ
#   credible_interval_99  — ±3σ
```

**Dependencies:** None

### `update_belief_with_history()` — Stateful Sequential Update

```python
from bayesian import EstimationLog, Observation, update_belief_with_history

log = EstimationLog(
    prior=Prior(mean=1.0, variance=0.25),
    observation_noise=0.15,
)

# Each call appends observations and records intermediate posteriors
posteriors = update_belief_with_history(log, [
    Observation(estimated=5, actual=7),
    Observation(estimated=10, actual=13),
])

# log.history contains all intermediate posteriors
# posteriors[-1] is the current belief
```

**Dependencies:** None

### `adjust_estimate()` — PERT Bridge

```python
from bayesian import adjust_estimate

result = adjust_estimate(pert_expected=12.0, posterior=posterior)
# Returns:
# {
#     "pert_expected": 12.0,
#     "delay_factor": 1.309,
#     "adjusted_expected": 15.7,
#     "adjusted_range_68": [14.98, 16.44],
#     "adjusted_range_95": [14.28, 17.14],
#     "n_observations": 6,
#     "confidence": "good — converging",
# }
```

**Dependencies:** None

### `visualise_belief_evolution()` — Belief Narrowing Plot

```python
from bayesian import visualise_belief_evolution

fig = visualise_belief_evolution(log, save_path="belief_evolution.png")
```

Shows the prior distribution narrowing into a tight posterior as observations accumulate — the visual proof that sequential Bayesian updating works.

**Dependencies:** `matplotlib`, `numpy`

## The Maths

Conjugate normal-normal updating. The delay factor `r = actual / estimated` is the signal.

**Prior:** `N(μ₀, σ₀²)` — our initial belief about the delay factor.

**For each observation with delay factor r:**

```
τ_prior = 1/σ²    (precision = inverse variance)
τ_obs   = 1/σ²_obs

τ_post  = τ_prior + τ_obs        (precisions add)
μ_post  = (τ_prior × μ + τ_obs × r) / τ_post
σ²_post = 1 / τ_post
```

Sequential processing is mathematically equivalent to batch — process all observations at once or one at a time, same result. The sequential form makes belief evolution visible.

### Why Not Just Average?

A simple mean of delay factors ignores:

1. **Prior knowledge** — If you know nothing, `N(1.0, 0.25)` encodes that honestly. If you have domain expertise ("auth tasks always run late"), you can start with `N(1.3, 0.1)`.
2. **Uncertainty quantification** — The posterior variance tells you how confident the calibration is. Three observations give wide intervals; thirty give narrow ones.
3. **Observation weighting** — Bayesian updating naturally weights new evidence against prior confidence. Early observations shift the belief dramatically; later ones refine it.

## Per-Context Calibration

Different task categories have different bias profiles:

```python
from bayesian import Prior, Observation, update_belief

shared_prior = Prior(mean=1.0, variance=0.25)

# Auth tasks: consistently late
auth_obs = [
    Observation(estimated=5, actual=7, context="auth"),
    Observation(estimated=10, actual=13, context="auth"),
]
auth_post = update_belief(shared_prior, auth_obs)
# delay factor ≈ 1.31

# Infra tasks: roughly on time
infra_obs = [
    Observation(estimated=5, actual=5.2, context="infra"),
    Observation(estimated=10, actual=9.8, context="infra"),
]
infra_post = update_belief(shared_prior, infra_obs)
# delay factor ≈ 1.02

# Same PERT estimate, very different adjusted durations
```

In the FastAPI integration, `context` becomes a first-class query parameter — ask for the delay factor for auth tasks specifically.

## Dependencies

| Function | Requires |
|----------|----------|
| `update_belief()` | Nothing |
| `update_belief_with_history()` | Nothing |
| `adjust_estimate()` | Nothing |
| `visualise_belief_evolution()` | matplotlib, numpy |

## Testing

```bash
# Run built-in examples and verification
python bayesian.py

# The worked examples verify against hand-computed values
```

## Licence

MIT — Use it however you want.

---

**Philosophy:** Estimates improve when you measure how wrong they were.

*"In God we trust. All others must bring data."* — W. Edwards Deming
