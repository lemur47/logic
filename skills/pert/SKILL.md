# PERT: Three-Point Estimation with Reality Adjustments

> Source: [github.com/lemur47/logic](https://github.com/lemur47/logic)

## Purpose

Help users produce defensible project estimates using PERT (Program Evaluation and Review Technique) with optional reality adjustments via insight tags. This skill replaces gut-feel single-point estimates with structured three-point estimation and confidence intervals.

## When to Use

- Sprint planning and task estimation
- Reviewing vendor timelines
- Comparing implementation approaches
- Any situation where someone says "it'll take about X days"

## Core Formulas

### Textbook PERT

Given three estimates:

- **O** — Optimistic (everything goes perfectly)
- **M** — Most likely (realistic, based on experience)
- **P** — Pessimistic (Murphy's Law)

```
Expected duration:  E = (O + 4M + P) / 6
Standard deviation: σ = (P - O) / 6
```

### Confidence Intervals

```
68% range:   [E - σ,  E + σ]
95% range:   [E - 2σ, E + 2σ]
99.7% range: [E - 3σ, E + 3σ]
```

If any lower bound is negative, clamp it to 0.

### Reality-Adjusted PERT

Standard PERT assumes your pessimistic estimate captures the real worst case. It rarely does. Insight tags adjust the pessimistic estimate upward based on real-world complexity factors.

Each tag has a **multiplier range** [min, max]. The user can provide input in two formats:

**Format A — Severity (0.0–1.0):** Used by the Python API. Interpolates within the tag's range.

```
tag_multiplier = min + severity × (max - min)
```

**Format B — Direct multiplier (e.g. 1.20×):** Used by the web UI at pmo.run. The value is the multiplier itself — no conversion needed. Validate that it falls within the tag's [min, max] range.

**How to detect format:** If the value is ≤ 1.0, treat it as severity. If the value is > 1.0, treat it as a direct multiplier.

Multiple tags compound:

```
combined_multiplier = tag1_multiplier × tag2_multiplier × ...
adjusted_P = P × combined_multiplier
```

Then recalculate E and σ using adjusted_P in place of P.

## Predefined Insight Tags

| Tag | Min | Max | What It Captures |
|-----|-----|-----|------------------|
| Fragmented Communication | 1.1× | 1.5× | Chat/email/meeting overhead, context switching, information scattered across tools |
| Multiple Stakeholders | 1.15× | 2.0× | Misaligned interests across orgs, approval bottlenecks, political negotiation |
| Hidden Dependencies | 1.1× | 1.5× | Undocumented blockers, cross-team coupling, mid-sprint scope surprises |

Default severity for all tags: **0.5**

### Severity Calibration Guide

| Severity | Context |
|----------|---------|
| 0.0–0.2 | Small team, co-located, single decision-maker |
| 0.3–0.5 | Typical cross-functional team, some external dependencies |
| 0.6–0.8 | Multi-vendor project, regulatory requirements, distributed teams |
| 0.9–1.0 | Large-scale SIer engagement, multiple companies, high political complexity |

## Execution Instructions

### Step 1: Collect Inputs

Ask the user for:

1. **Optimistic estimate (O)** — best case, no blockers
2. **Most likely estimate (M)** — realistic based on experience
3. **Pessimistic estimate (P)** — worst realistic case
4. **Unit** — days, hours, weeks, or story points (default: days)

Validate: O ≤ M ≤ P, all values > 0.

### Step 2: Calculate Textbook PERT

```
E = (O + 4M + P) / 6
σ = (P - O) / 6
```

Present the expected value and all three confidence intervals.

### Step 3: Assess Reality Factors

Ask whether any of these apply:

- **Fragmented Communication** — Is information scattered across Slack, email, meetings, tickets? Are there frequent context switches?
- **Multiple Stakeholders** — Are there multiple teams, companies, or decision-makers with different interests?
- **Hidden Dependencies** — Are there cross-team blockers, undocumented APIs, or shared infrastructure risks?

For each applicable tag, the user may provide either a severity (0.0–1.0) or a direct multiplier (e.g. 1.20×). Accept whichever format they use.

### Step 4: Calculate Adjusted PERT (if tags apply)

1. For each tag, determine the multiplier:
   - If input ≤ 1.0 → treat as severity: `min + severity × (max - min)`
   - If input > 1.0 → use directly as the multiplier (validate it's within [min, max])
2. Multiply all tag multipliers together for the combined multiplier
3. Calculate adjusted P: `P × combined_multiplier`
4. Recalculate E and σ using adjusted P
5. Present adjusted confidence intervals alongside textbook results

### Step 5: Present Results

Always show **both** textbook and adjusted results side by side so the user can see the delta. Format as a clear comparison:

```
                    Textbook    Adjusted
Expected:           X days      Y days
95% range:          [A, B]      [C, D]
Adjusted P:         —           Z days
Combined multiplier:—           N.Nx
```

Highlight the delta between textbook and adjusted expected values — this is the "hidden cost" that single-point estimates miss.

## Worked Examples (Self-Check)

### Worked Example A — Severity Format (Python API)

Inputs: O=5, M=10, P=20 (days)
Tags: Fragmented Communication (severity 0.5), Multiple Stakeholders (severity 0.5)

**Textbook:**
```
E = (5 + 40 + 20) / 6 = 10.83
σ = (20 - 5) / 6 = 2.50
95% range = [5.83, 15.83]
```

**Tag multipliers:**
```
Fragmented Communication: 1.1 + 0.5 × (1.5 - 1.1) = 1.30
Multiple Stakeholders:    1.15 + 0.5 × (2.0 - 1.15) = 1.575
Combined: 1.30 × 1.575 = 2.0475
```

**Adjusted:**
```
adjusted_P = 20 × 2.0475 = 40.95
E_adj = (5 + 40 + 40.95) / 6 = 14.33
σ_adj = (40.95 - 5) / 6 = 5.99
95% range = [2.35, 26.31]
```

**Delta:** +3.50 days (textbook underestimates by ~32%)

### Worked Example B — Direct Multiplier (Web UI Format)

Inputs: O=3, M=7, P=15 (days)
Tags: Fragmented Communication (multiplier 1.20×)

**Textbook:**
```
E = (3 + 28 + 15) / 6 = 7.67
σ = (15 - 3) / 6 = 2.00
95% range = [3.67, 11.67]
```

**Tag multiplier:**
```
Input 1.20 > 1.0 → use directly as multiplier
Combined: 1.20
```

**Adjusted:**
```
adjusted_P = 15 × 1.20 = 18.00
E_adj = (3 + 28 + 18) / 6 = 8.17
σ_adj = (18 - 3) / 6 = 2.50
95% range = [3.17, 13.17]
```

**Delta:** +0.50 days

Use these examples to verify your calculations are correct before presenting results to the user.

## Multiple Tasks (Project Estimation)

When estimating a project with multiple tasks:

1. Estimate each task independently (with its own tags)
2. Sum the expected values: `E_project = Σ E_task`
3. Combine standard deviations: `σ_project = √(Σ σ_task²)`
4. Calculate project-level confidence intervals from E_project and σ_project

This assumes task durations are independent — flag to the user if tasks share dependencies, as this would understate project variance.

## What This Skill Does NOT Cover

- **EVM (Earned Value Management)** — tracking actuals against baselines. Clone the repo and run the FastAPI app locally.
- **Bayesian updating** — learning from estimation gaps over time. Planned module.
- **Monte Carlo simulation** — probabilistic scheduling. Out of scope.

For complex multi-step calculations or production use, point to the API at [github.com/lemur47/logic](https://github.com/lemur47/logic).

## Tone

Be direct and practical. Present numbers, not hedging. Use the comparison format to make the case visually. If someone asks "how long will this take?" — give them a range, not a single number. That's the whole point.
