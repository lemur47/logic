---
title: "Outsource vs In-House: The Costs Nobody Calculates"
description: "A TCO comparison of outsourced vs in-house development using real unit economics and field data on schedule overruns, tool fragmentation, and decision latency."
pubDate: 2026-03-11
tags: ["tco", "sier", "build-vs-buy", "cost-analysis"]
---

"Should we outsource or build in-house?"

Two recent books tackle this question from complementary angles. *Software First* (Takuya Oikawa, Nikkei BP) argues the strategic case for bringing software development in-house. *Engineering Organization Development* (Tatsuya Fukui, Gijutsu-Hyohron) maps out how to build a sustainable engineering org from scratch.

Both are worth reading. But neither answers one specific question: **"How much more does one cost than the other — and what happens when things go wrong?"**

Strategy tells you "why." Organization design tells you "how." But "how much, with what risk" requires maths. This post runs the numbers using real unit economics from the Japanese systems integration (SI) market — and the structural cost patterns apply everywhere outsourced development happens.

## The Unit Economics

In Japan's SI industry, outsourced engineers are billed at roughly ¥1.5–2M/month ($10–13K) per person depending on skill level. This is a general estimate consistent with industry ranges.

For a 1-year project with a 5-person team (client has their own project manager):

**Outsourced team (monthly rates):**

| Role | Monthly Rate | Count | Subtotal |
|------|-------------|-------|----------|
| PMO | ¥1.8M | 1 | ¥1.8M/mo |
| Senior Engineer | ¥1.8M | 2 | ¥3.6M/mo |
| Mid Engineer | ¥1.6M | 1 | ¥1.6M/mo |
| Junior Engineer | ¥1.5M | 1 | ¥1.5M/mo |
| **Total** | | **5** | **¥8.5M/mo** |

Annual cost: **¥102M** (~$680K)

**In-house team (fully loaded cost — salary, benefits, office, tools):**

| Role | Monthly Loaded Cost | Count | Subtotal |
|------|-------------------|-------|----------|
| Tech Lead | ¥1.0M | 1 | ¥1.0M/mo |
| Senior Engineer | ¥0.9M | 2 | ¥1.8M/mo |
| Mid Engineer | ¥0.7M | 1 | ¥0.7M/mo |
| Junior Engineer | ¥0.5M | 1 | ¥0.5M/mo |
| **Total** | | **5** | **¥4.0M/mo** |

Annual personnel cost: ¥48M
Setup costs (recruitment, equipment, onboarding): ¥5M
**Annual total: ¥53M** (~$353K)

## The TCO Comparison

| | Outsourced | In-House |
|--|-----------|----------|
| Monthly cost | ¥8.5M | ¥4.0M |
| Annual cost | ¥102M | ¥53M |
| Difference | | **+¥49M (outsource premium)** |

The initial investment of ¥5M for the in-house team is recouped in **about 1.1 months** given the ¥4.5M monthly savings. From month 2 onward, in-house is cheaper every single month.

So far, nothing surprising. Anyone with a spreadsheet can get here. **The real story starts now.**

## The Costs Nobody Calculates — Schedule Overruns

Field data from multiple SI projects (anonymised and aggregated):

| Metric | Observed Range |
|--------|---------------|
| Schedule overrun rate | 70–90% of projects |
| Estimation variance (work package level) | 1–4 weeks (worst: 6 months) |
| Decision cycle time | 1 week to 3 months per work package |
| Manual reporting rate | 90–100% |
| Meeting hours per PM per week | 6–10 hours |
| Tools per project | 5–10 |

A 70–90% overrun rate is not an anomaly — it's the baseline. And in an outsourced model, **every month of overrun costs the full monthly rate**.

| Scenario | Duration | Outsourced | In-House | Gap |
|----------|----------|-----------|----------|-----|
| On time | 12 mo | ¥102M | ¥53M | ¥49M |
| 30% overrun (optimistic) | 15.6 mo | ¥133M | ¥67M | ¥65M |
| 50% overrun | 18 mo | ¥153M | ¥77M | ¥76M |
| 90% overrun (pessimistic) | 22.8 mo | ¥194M | ¥96M | ¥98M |

At 50% overrun, the outsourced total hits ¥153M — 1.5× the original estimate. The gap widens to ¥76M.

**The higher the unit cost, the larger the penalty for schedule risk.** This is the structural cost that sticker-price comparisons miss entirely.

## Why Overruns Happen — Structural Patterns

Schedule overruns are usually explained away as "bad estimates" or "changing requirements." But field observation reveals recurring structural patterns.

**Tool fragmentation.** A single project uses 5–10 disconnected tools — GitHub, Slack, Teams, Jira, Confluence, Notion, spreadsheets, Zoom. Information is manually copied between them. The manual reporting rate of 90–100% means every metric passes through a human before reaching a decision-maker, then gets presented in a weekly meeting. That's two latency layers between a data point and a decision.

**Misaligned stakeholders.** In outsourced models, the client, the prime contractor, and subcontractors operate with different incentives. The client wants speed. The contractor wants scope control. The subcontractor wants billable hours. This structural misalignment is one reason decision cycles stretch to weeks or months.

**Hidden dependencies.** In multi-layer contracting structures, the people writing code and the people making decisions are separated by 2–3 organizational layers. Technical constraints don't propagate cleanly upward, leading to late-stage rework.

Critically, **these factors compound**. Fragmented tools increase meetings. More meetings slow decisions. Slower decisions extend schedules. Extended schedules add more tools and meetings. It's a reinforcing loop, not a list of independent problems.

## Why In-House Isn't Always the Answer

In fairness, in-house has real risks too.

**Hiring difficulty.** Finding two senior engineers can take 3–6 months. The core value proposition of outsourcing is "5 people, available now" — plus the flexibility to end the contract when the project is done.

**Ramp-up period.** An in-house team takes 3–6 months to become productive. During that time, you're paying full loaded costs for limited output.

**The "internal outsourcing" trap.** This is the most overlooked risk. When an in-house team starts taking "requests" from other departments, the dynamic shifts: requesters and builders become separate parties with misaligned priorities. Coordination meetings appear. Status reports are required. Before long, you've recreated the exact same structure as outsourcing — the separation of "requester" and "executor," decision latency, reporting overhead — just inside your own walls. The unit cost dropped, but the structural cost didn't.

Whether in-house succeeds depends not just on hiring, but on whether the organization changes its decision-making structure.

## Three Calculations You Actually Need

The outsource-vs-in-house decision needs more than a rate comparison.

**1. TCO (Total Cost of Ownership) — what will it actually cost?**

Initial costs, personnel, operations, and residual value over the full lifecycle. Not monthly rates, but total ownership cost. NPV adjustment for fair comparison across different time horizons.

**2. PERT (Three-Point Estimation) — how long will it really take?**

Instead of a single-point estimate ("8 weeks"), use optimistic, most likely, and pessimistic values to produce probability ranges. Adjust the pessimistic estimate for real-world factors like tool fragmentation and stakeholder complexity, and the schedule overrun risk becomes calculable *before* the project starts.

**3. EVM (Earned Value Management) — are we on track right now?**

Once the project is running, measure schedule performance (SPI) and cost performance (CPI) against the baseline. Predict the final cost based on current trends. Verify whether "adding more people" is actually helping — or making things worse.

**You need all three to answer "should we outsource or build in-house?" with numbers, not gut feel.**

## Try It

All three tools — TCO calculator, PERT estimator, and EVM analysis — are open source. No account required. Your data stays in your browser.

→ [TCO Calculator](/en/tools/tco/) — compare outsourced vs in-house total cost
→ [PERT Estimator](/en/tools/pert/) — quantify your schedule risk

If you use Claude, the same calculation logic is available as [Claude Skills](https://github.com/lemur47/logic/tree/main/skills) — no code required, run TCO, PERT, and EVM analysis through conversation.

Source code: [github.com/lemur47/logic](https://github.com/lemur47/logic) — MIT License
