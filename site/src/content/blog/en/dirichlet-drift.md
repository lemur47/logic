---
title: "Turn What Your Team Already Knows Into a Smarter Forecast"
description: "Your team has years of delivery data. Your schedule forecast ignores all of it. Drift correction changes that — feeding past performance back into the model so your next forecast is sharper than the last."
pubDate: 2026-05-04
tags: ["monte-carlo", "dirichlet", "estimation", "pmo"]
---

You have the data. It is sitting in your CI/CD logs, your sprint reports, your retrospective notes. Hundreds of tasks — estimated, delivered, closed. And when you estimate the next project, you start from scratch.

Every PMO does this. Every schedule simulation treats the organisation as if it has never shipped anything before. The optimistic-most-likely-pessimistic estimates go in, the engine runs ten thousand scenarios, and out comes a finish date you would bet on — the one with an 85% chance of being right. It is a good number. But it is a number with no memory.

What if it did?

## The Gap Between "We Know" and "We Use"

Ask any DevOps lead and they will tell you: "Security hardening always takes longer than we think." Ask any product manager and they will say: "Stakeholder alignment eats two weeks every time." They know this. They have lived it across dozens of releases.

But that knowledge stays in their head. It does not flow into the forecast. The simulation treats a security hardening task the same as a deployment automation task — same distribution shape, same assumptions, same blind optimism.

This is the gap. Not a lack of data. Not a lack of intuition. A lack of connection between the two.

Think of it this way. You run a restaurant. You know that Friday evenings are busy and Tuesday lunchtimes are quiet. You would not staff both shifts the same way. But that is exactly what a standard schedule simulation does with your project — it staffs every task the same way, regardless of what you already know about how that type of work actually behaves.

## What If the Forecast Could Learn?

The idea is simple. Before you run the simulation, look at how similar tasks performed in the past. If security hardening tasks historically took 140% of their most-likely estimate, tell the model. If deployment automation came in at 90%, tell it that too.

We call this *drift*. Each task category gets a drift factor — a multiplier that shifts the simulated duration up or down based on what actually happened before.

![Drift correction workflow: team experience and delivery history feed into category drift factors, which drive a schedule simulation to produce a confident finish date. New actuals loop back as input.](/blog/dirichlet-drift/drift-correction-workflow.svg)

Here is the key move: you do not pick a single drift number and hard-code it. You let the model express uncertainty about the drift itself. Maybe security hardening overran by 140% on average, but some sprints saw 120% and others saw 180%. That spread matters. A model that says "140% ± 30%" is more honest than one that says "140%, full stop."

This is where a distribution called the Dirichlet comes in. Do not worry about the name — what it does is straightforward. It takes your task categories and assigns uncertain weights to each one. Those weights shift from simulation to simulation. The result is a forecast that does not just simulate duration uncertainty — it simulates *how sure we are about the pattern* too.

Plain version:

- **Without drift:** "This task could take 5–12 days." (Same assumption for every task type.)
- **With drift:** "This task could take 5–12 days, but tasks like this one have historically run long, so the forecast leans toward 8–15 days. How far it leans depends on how much history we have."

That second version is closer to how an experienced engineer or PM actually thinks. The difference is that now the thinking is in the model, not just in someone's head.

## What This Looks Like in Practice

Two examples — one from a DevOps team, one from a product organisation.

### The DevOps Team

A platform engineering team is planning a major infrastructure upgrade: new container orchestration, secrets management overhaul, observability stack migration, and CI pipeline rebuild. Eight workstreams, twelve-week target.

The team lead has been through three similar upgrades. She knows the pattern. But the project simulation does not.

When she pulls the actuals from the last two years, sorted by task category, the data confirms what she already felt:

- **Security and compliance** tasks consistently overrun. Average actual is 142% of the most-likely estimate. The spread is moderate — the team just chronically underestimates the review-and-remediation cycle.
- **CI/CD pipeline work** comes in close to estimate. Average is 98%, tight spread. The team knows this domain cold.
- **Observability and monitoring** tasks are the wild card. Average is 118%, but the spread is enormous — some at 85%, others at 175%. It depends heavily on which third-party integrations are involved.

With a standard simulation, none of this matters. Every task gets the same treatment. The confident finish date comes out at 14 weeks.

With drift correction:

- Security tasks get pulled toward longer durations. The forecast accounts for the team's consistent underestimation.
- CI/CD work stays where it is. The team's estimates are already reliable here.
- Observability tasks get a wide, uncertain drift — the model honestly says "the historical bias is upward, but we are not confident by how much."

The drift-corrected finish date comes out at 16.5 weeks. Two and a half weeks of difference — not because the estimates changed, but because the forecast finally listened to what the team lead already knew.

More importantly, the model now shows *where* the risk concentrates. Security is a known, predictable overrun — budget for it. Observability is where the genuine uncertainty lives. That distinction changes the conversation from "are we on track?" to "where should we focus our attention?"

### The Product Team

A product organisation is building a new feature set: user research, UX design, frontend development, backend API work, integration testing, and a phased rollout. The product manager has a quarterly target.

This team has a different data shape. Their actuals tell a story about organisational friction, not technical complexity:

- **UX research and design** tasks overrun by 125% on average — but not because the designers are slow. Stakeholder feedback loops extend every review cycle. The drift is structural, not individual.
- **Frontend development** is bimodal. Simple UI work comes in at 95%. Anything involving accessibility compliance or cross-browser edge cases hits 155%. The average drift of 115% hides two very different realities.
- **Stakeholder alignment and sign-off** is the silent schedule killer. Average drift is 160%, standard deviation is huge. Some features sail through. Others get stuck in three rounds of executive review. The team has learned to pad, but they pad inconsistently.

A standard simulation sees none of this. It treats sign-off as a three-day task with a range of 2–5 days.

With drift correction, the model learns that sign-off is really a 3–8 day task that clusters around 5 days, with a long tail toward 12 when the feature is commercially sensitive. That one adjustment alone can shift the confident finish date by a week.

The product manager does not need to understand the mathematics. What she needs is a forecast that reflects the organisation she actually works in — not the idealised one that the estimates describe.

## Under the Bonnet

*This section is for the technically curious. The practical takeaways are in the next section — skip ahead if you prefer.*

The drift mechanism works in two layers.

**Layer 1: Posterior estimates from history.** For each task category, we compute a posterior distribution over the drift factor using observed estimate-vs-actual ratios. If security tasks show a mean drift of 1.42 with a standard deviation of 0.15, the posterior is N(1.42, 0.15). More observations tighten the posterior. Fewer observations keep it wide — the model hedges honestly rather than pretending to know.

**Layer 2: Dirichlet weighting across categories.** When a task belongs to a known category, it gets that category's drift directly. When a task is unclassified or straddles categories, the model draws a weight vector from a Dirichlet distribution and blends the drifts. The Dirichlet ensures the weights sum to 1 and that the blend itself is uncertain — different simulations explore different category mixes.

The maths reduces to one equation per simulation:

```
drift_j = Σ_k [ w_k × μ_k ]
```

where `w_k` is the Dirichlet-sampled weight for category `k`, and `μ_k` is the posterior mean drift for that category. The sampled task duration is then multiplied by `drift_j`.

Two properties make this trustworthy:

1. **Degenerate reducibility.** If all posteriors are neutral (drift = 1.0, no historical signal), the model collapses to a standard simulation. You get the same answer you would have got before. Drift is purely additive — it cannot make things worse.

2. **Monotonic learning.** As you feed in more data, the posteriors tighten. The model becomes more confident, but only because you earned it with data, not because you assumed it away.

The implementation is open source at [github.com/lemur47/logic](https://github.com/lemur47/logic). The standalone proof of concept is in `examples/standalone/montecarlo/dirichlet_drift.py` — 23 tests covering six validation categories, runnable with `pytest`.

## Three Things You Can Do Next Sprint

You do not need to deploy a drift model to start benefiting from this thinking. Here are three steps any team can take immediately.

**1. Start tracking estimate-vs-actual by task category.**

When a task closes, record the original estimate alongside the actual duration. Tag it with a category — even a rough one like *development*, *infrastructure*, *review*, *external dependency*. After 20–30 completed tasks per category, you have enough signal to see the pattern.

If you already track actuals but not categories, add a single field to your tracker. One column. That is the minimum viable data pipeline.

**2. Compute your category drift factors.**

For each category, divide actual duration by most-likely estimate across all completed tasks. The mean is your average bias. The standard deviation tells you how confident you should be in that bias.

A drift of 1.4 with a standard deviation of 0.05 says: "This type of work consistently overruns by 40%, and we are quite sure about that." A drift of 1.15 with a standard deviation of 0.4 says: "This type of work tends to overrun, but we honestly do not know by how much." Both are useful. The second is more honest, and honesty is what makes a forecast trustworthy.

**3. Run a before-and-after comparison on your current programme.**

Take your next schedule simulation and run it twice: once without drift, once with your historical drift factors applied. Compare the confident finish dates. If they are close, your estimates are already well-calibrated — congratulations. If they diverge, you have just found the gap between what your estimates say and what your organisation actually delivers. That gap is the conversation your steering committee needs to have.

---

*This post is part of the [pmo.run](https://pmo.run) series on turning project data into decision intelligence. The drift correction module is open source and available at [github.com/lemur47/logic](https://github.com/lemur47/logic). The previous post — [Your Estimate Is a Dot. Here's the Shape It's Hiding.](/en/blog/monte-carlo-your-estimate-is-a-dot/) — covers the simulation foundation that drift builds on.*
