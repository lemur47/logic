---
title: "Why LLMs Can't Learn from Your Estimation Errors"
description: "LLMs plateau after a single observation when updating beliefs. For PMOs that need to learn from estimation history, you need deterministic Bayesian maths underneath — not just chat."
pubDate: 2026-03-24
tags: ["bayesian", "estimation", "llm", "pert", "project-management"]
---

Ask your AI assistant: "Our auth tasks consistently take 30% longer than estimated. What should I adjust my next estimate to?"

You'll get a plausible answer. It might even be close. But ask it again after five more data points, and the answer won't be meaningfully better. The AI hasn't *learned* from the additional evidence — it's pattern-matching each time from scratch.

This is not a prompt engineering problem. It's a mathematical limitation. And if your PMO is using AI-assisted estimation, it matters.

## The Estimation Problem

Every PMO has a spreadsheet somewhere with estimated vs actual durations. Most ignore it. The ones that don't usually compute an average and call it a "lessons learned."

But averages are crude. They treat the first observation and the fiftieth equally. They don't tell you how confident you should be. And they don't get sharper as you collect more data.

What you actually want is a system that:

- Starts with an honest "we don't know" prior
- Gets more precise with every completed task
- Tells you *how certain* it is, not just what it thinks
- Distinguishes between task categories (auth is different from infrastructure)

That's Bayesian updating. And it's been solved mathematics since the 18th century.

## How Bayesian Calibration Works

The idea: every completed task produces a *delay factor* — the ratio of actual duration to estimated duration. A task estimated at 10 days that takes 13 has a delay factor of 1.3.

We model the true systematic bias as a Gaussian distribution. We start with a prior belief — "we think estimates are roughly right, but we're not very sure" — and update it with every observation.

The update rule uses precision (the inverse of variance). Precisions add:

```
τ_posterior = τ_prior + τ_observation
```

The posterior mean is a precision-weighted average of the prior and the new data:

```
μ_posterior = (τ_prior × μ_prior + τ_obs × r) / τ_posterior
```

This is conjugate normal-normal updating. Each observation tightens the distribution. The posterior after observation *n* becomes the prior for observation *n+1*. Knowledge compounds.

Here's what it looks like in Python:

```python
def update_belief(prior, observations, observation_noise=0.15):
    noise_variance = observation_noise ** 2
    tau_obs = 1.0 / noise_variance

    mu = prior.mean
    tau = 1.0 / prior.variance

    for obs in observations:
        r = obs.actual / obs.estimated  # delay factor
        tau_new = tau + tau_obs
        mu_new = (tau * mu + tau_obs * r) / tau_new
        tau = tau_new
        mu = mu_new

    return Posterior(mean=mu, variance=1.0 / tau)
```

Six lines of maths. No neural network. No training data. No GPU.

## A Worked Example: SIer Auth Tasks

Suppose your team has completed six authentication tasks. Each took longer than estimated:

| Task | Estimated | Actual | Delay factor |
|------|-----------|--------|-------------|
| Login flow | 5 days | 7 days | 1.40 |
| OAuth integration | 10 days | 13 days | 1.30 |
| Session handling | 3 days | 4 days | 1.33 |
| Token refresh | 8 days | 10 days | 1.25 |
| RBAC module | 15 days | 19 days | 1.27 |
| MFA implementation | 6 days | 8 days | 1.33 |

Starting from an uninformative prior — N(1.0, 0.25), meaning "we think there's no bias but we're not sure" — the posterior narrows with each observation:

| After obs | Posterior mean | Posterior σ | 95% CI |
|-----------|---------------|-------------|--------|
| 1 | 1.367 | 0.144 | [1.09, 1.65] |
| 2 | 1.335 | 0.104 | [1.13, 1.54] |
| 3 | 1.334 | 0.085 | [1.17, 1.50] |
| 4 | 1.314 | 0.074 | [1.17, 1.46] |
| 5 | 1.305 | 0.067 | [1.17, 1.43] |
| 6 | 1.309 | 0.061 | [1.19, 1.43] |

After six observations, the system is confident: auth tasks take approximately 131% of the PERT estimate, give or take 6%. The 95% credible interval has collapsed from [0.02, 1.98] to [1.19, 1.43].

Now apply this to a new estimate. PERT says a new auth task will take 12 days:

- **Calibrated estimate:** 15.7 days
- **95% range:** [14.3, 17.1] days
- **Confidence:** good — converging

Compare this with infrastructure tasks from the same team, which have a delay factor of 1.027. Same PERT formula, same team, but auth tasks need 2.8 more days per 10-day estimate. That's the calibration insight that flat PERT cannot provide.

## Why LLMs Can't Do This

[In 2026, Qiu et al. published a study in Nature Communications](https://www.nature.com/articles/s41467-025-67998-6) examining whether large language models can perform probabilistic reasoning — specifically, sequential Bayesian belief updating.

Their key finding: off-the-shelf LLMs plateau after a single observation. They can incorporate one piece of evidence into their reasoning, but they cannot progressively refine beliefs across multiple rounds. The precision-accumulation mechanism — where each observation compounds knowledge from all previous ones — simply doesn't happen inside an LLM's forward pass.

This isn't surprising if you think about how LLMs work. Each inference call is stateless. The model doesn't carry forward an internal probability distribution that narrows over time. It generates text that *looks* like Bayesian reasoning, but the actual mathematical precision accumulation isn't there.

The researchers found that a "Bayesian teaching" approach — fine-tuning LLMs on intermediate reasoning traces — improved performance. But even then, the model is learning to *mimic* Bayesian updates, not *perform* them. The deterministic maths is still more reliable, more auditable, and infinitely cheaper to run.

[A 2026 Stanford working paper on FOMC policy simulation](https://digitaleconomy.stanford.edu/publication/fomc-in-silico-a-multi-agent-system-for-monetary-policy-decision-modeling/) reinforces this from a different angle. Their dual-track framework runs an LLM-based deliberation track alongside a separate Monte Carlo/Bayesian track — using the exact same conjugate normal-normal update formulas as our module. The LLM handles natural language deliberation (what the policy should be and why). The Bayesian track handles the maths (what the numbers say). Neither tries to do the other's job.

## The Two-Tier Architecture

The pattern that emerges from both papers — and from our own engineering — is a clean separation:

**Layer 1: Deterministic maths.** Bayesian updating, PERT estimation, EVM metrics. Pure Python. No LLM. Auditable, reproducible, compounding. This is where sequential precision accumulation lives.

**Layer 2: LLM interpretation.** The model reads the structured posterior — "delay factor 1.31, σ=0.061, confidence: good" — and produces natural language insight. "Auth tasks consistently overrun by about 30%. Consider adding a 3-day buffer to any auth estimate, or investigate why the OAuth integration pattern recurs."

The LLM adds value at the boundary: translating numbers into decisions, generating recommendations, explaining anomalies in context. But the numbers themselves must come from deterministic logic. If the maths is wrong, no amount of eloquent interpretation fixes it.

In code:

```python
# Layer 1: deterministic — this MUST be exact
posterior = update_belief(prior, observations)

# Layer 2: LLM interpretation — reads structured output
prompt = f"""
The Bayesian analysis shows:
- Delay factor: {posterior.mean:.3f}
- Confidence interval: {posterior.credible_interval_95}
- Based on {posterior.n_observations} observations

What should the project manager do?
"""
```

The LLM never touches the update formula. It reads the result.

## Where This Leads

We've open-sourced the Bayesian estimation calibration module as part of our [logic toolkit](https://github.com/lemur47/logic). It's the fourth module in the Performance family: PERT estimates the duration, Bayesian calibration learns how wrong PERT is, and (coming next) Monte Carlo simulation propagates that uncertainty across an entire project schedule.

The calibration module supports:

- Per-category contexts (auth, infrastructure, frontend — each with its own learned bias)
- Configurable priors and observation noise
- Both stateless calculation and persistent context tracking via the API
- Direct integration with PERT estimates

The maths is MIT-licensed. The API is live. The field-calibrated adjustment coefficients that make it accurate for specific industries — those are the consulting layer on top.

If your AI tools are giving you single-point estimates without learning from your estimation history, they're leaving the most valuable data on the table. The fix isn't a better prompt. It's a deterministic module underneath.

---

*The Bayesian estimation module is available at [github.com/lemur47/logic](https://github.com/lemur47/logic). The mathematical formulations are adapted from the conjugate normal-normal framework validated in Kazinnik & Sinclair (2026) for FOMC policy simulation, with the LLM belief updating limitation established by Qiu et al. (2026) in Nature Communications.*
