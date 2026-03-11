---
title: "Why Your Project Estimates Are Always Wrong"
description: "PERT has been around since the 1950s. It's still not enough. Here's what's missing — and the maths to fix it."
pubDate: 2026-02-22
tags: ["pert", "estimation", "project-management"]
---

"This task? Should take about two weeks."

Three months later, the task is still in progress. The original estimate wasn't stupid — it was incomplete. And the gap between "should take" and "actually took" is where most project failures hide.

This post explains why, gives you the maths to prove it, and offers a free tool to stop it from happening.

## The Textbook Answer

PERT (Program Evaluation and Review Technique) has been around since the 1950s. The idea is simple: instead of guessing one number, you give three.

- **Optimistic (O):** Everything goes perfectly. No blockers, no surprises.
- **Most likely (M):** The realistic case. You've done this before, it usually takes about this long.
- **Pessimistic (P):** Murphy's Law. Dependencies break, people are unavailable, scope creeps.

The expected duration is a weighted average:

```
E = (O + 4M + P) / 6
```

The standard deviation tells you how uncertain that estimate is:

```
σ = (P - O) / 6
```

From these, you get confidence intervals. At 2σ (95% confidence), you're saying: "I'm 95% sure this task will finish within this range."

This is useful. It's a real improvement over single-point estimation. But in practice, it still underestimates. Consistently.

## Why Textbook PERT Fails

The formula assumes your pessimistic estimate actually captures the worst realistic case. It almost never does. Here's why.

### You Ignored Communication Costs

When you estimated "two weeks," you imagined the work itself — writing code, designing a schema, running tests. You didn't account for the 30-minute standup that runs 45 minutes. The Slack thread where three people debate a naming convention for two days. The approval workflow that requires a meeting, which requires an agenda, which requires a document nobody has time to write.

In fragmented communication environments — where information flows through chat, email, meetings, tickets, and hallway conversations — the overhead isn't additive. It's multiplicative. Every handoff is a potential misunderstanding. Every context switch is lost time.

### You Ignored Hidden Dependencies

Your task doesn't exist in isolation. It depends on an API that another team is still building. It touches a database migration that's blocked by a security review. A parallel task will change the interface you're building against, but nobody told you yet.

These dependencies are rarely captured in a backlog. They emerge mid-sprint, and each one adds not just time, but variance — the kind that your pessimistic estimate never included.

### You Ignored Stakeholder Misalignment

This is the big one, and the hardest to quantify.

When multiple companies and teams are involved in a project, they bring different *interests* to the table. Not just incentives — interests. The distinction matters.

**Incentives** are structural. They're baked into contracts, KPIs, and billing models. A vendor on time-and-materials billing has an incentive to extend timelines. A PM measured on on-time delivery has an incentive to pad estimates. These are observable and somewhat negotiable.

**Interests** are broader. They include strategic goals, political positioning, risk appetite, and reputation concerns — things nobody writes into a contract but that drive behaviour in every meeting. One team wants to ship fast to hit a quarterly target. Another team wants to delay because the feature threatens their domain ownership. A third team has already mentally moved on to the next project.

Same project. Fundamentally different interests. And the time it takes for these interests to converge — through negotiations, escalations, workarounds, and compromises — is the gap between your textbook estimate and reality.

In multi-company enterprise projects (SIer engagements, outsourced development, joint ventures), this factor alone can stretch a task from weeks to months.

## Modelling the Gap

Standard PERT can't capture these factors because they don't change the optimistic or most likely case. They inflate the tail — the pessimistic case — in ways that the original estimator didn't foresee.

We model this with **insight tags**: composable multipliers that adjust the pessimistic estimate based on real-world complexity factors.

```python
from pert import estimate_task, FRAGMENTED_COMMUNICATION, MULTIPLE_STAKEHOLDERS

# Textbook PERT
result = estimate_task(optimistic=5, most_likely=10, pessimistic=20)
# Expected: 10.83 days, 95% range: [5.83, 15.83]

# Reality-adjusted PERT
result = estimate_task(
    optimistic=5,
    most_likely=10,
    pessimistic=20,
    tags=[
        (FRAGMENTED_COMMUNICATION, 0.7),
        (MULTIPLE_STAKEHOLDERS, 0.6),
    ],
)
# Adjusted pessimistic: 45.82 days
# Expected: 15.14 days (textbook was 10.83)
```

The insight tags don't change your best or most likely case. They widen the tail — and since the expected value is a weighted average that includes the pessimistic estimate, it shifts too. Your two-week task is now realistically a three-week task, and the worst case nearly tripled.

Each tag has a severity parameter (0.0 to 1.0) that lets you calibrate based on your specific context. A two-person startup with one stakeholder? Low severity. A five-company SIer engagement with regulatory requirements? High severity on everything.

## The Mental Model

Textbook PERT asks: "How long will the *work* take?"

Reality-adjusted PERT asks: "How long will the *work, plus everything around the work,* take?"

The gap between these two questions is where project schedules die. The variables that kill your estimate — communication overhead, hidden dependencies, misaligned interests — aren't unknown. They're just unaccounted for. Every experienced PM has felt them. We just gave them a formula.

## Try It

The PERT module is open source and free to use:

```bash
git clone https://github.com/lemur47/logic.git && cd logic
python examples/standalone/pert/pert.py
```

It works as a standalone Python module with zero dependencies, or as part of the logic API.

The three built-in insight tags (fragmented communication, multiple stakeholders, hidden dependencies) come from real consulting experience in Japanese enterprise PMO environments. You can also create custom tags with your own multiplier ranges — every project has its own flavour of dysfunction.

## What's Next

This tool gives you better estimates. But better estimates are only valuable if you learn from the gap between prediction and outcome. That's where Bayesian updating comes in — using actual project results to calibrate your insight tag multipliers over time, so your estimates get more accurate as you go.

That's the next module on our roadmap. If you want to follow along: [github.com/lemur47/logic](https://github.com/lemur47/logic).
