# TCO: Total Cost of Ownership for Investment Decisions

> Source: [github.com/lemur47/logic](https://github.com/lemur47/logic)

## Purpose

Help users answer one question: **"What will this actually cost?"** using Total Cost of Ownership analysis. This skill replaces sticker-price comparisons with lifetime cost calculations that include maintenance, operations, time value of money, and residual value.

TCO is the financial foundation for PERT and EVM. PERT asks "how long will it take?" EVM asks "are we on track?" TCO asks "what's the real cost of each option?" — the question that should come first.

## When to Use

- Build vs buy decisions ("should we develop in-house or use SaaS?")
- Vendor and tool comparisons where upfront prices differ wildly
- Equipment or infrastructure lifecycle planning
- Any situation where someone says "Option B is cheaper" based on sticker price alone
- Justifying a higher upfront investment that saves money over time
- PMO value cases — quantifying the cost of the status quo vs. change

## Core Formulas

### Simple TCO (undiscounted)

```
Total operational = (annual_maintenance + annual_operating_cost) × useful_life_years
Total cost = initial_price + total_operational - residual_value
Annual cost = total_cost / useful_life_years
Monthly cost = annual_cost / 12
Daily cost = annual_cost / 365
```

This is the baseline. It answers "how much will this cost me per year, all-in?" without adjusting for inflation or opportunity cost.

### NPV-Adjusted TCO (time value of money)

```
NPV operational = Σ (annual_maintenance + annual_operating_cost) / (1 + discount_rate)^year
                  for year = 1 to useful_life_years

NPV residual = residual_value / (1 + discount_rate)^useful_life_years

NPV TCO = initial_price + NPV_operational - NPV_residual
NPV annual = NPV_TCO / useful_life_years
```

The discount rate accounts for the fact that money today is worth more than money tomorrow. Default: **3%** (conservative, roughly tracks long-term inflation). Adjust upward for high-interest environments or when capital has a clear alternative use.

**When to use NPV vs simple:** For short timeframes (1–3 years) or quick comparisons, simple TCO is sufficient. For long-lived assets (5+ years) or when comparing options with very different lifespans, NPV-adjusted TCO gives the fairer comparison.

### Break-Even Analysis

When comparing two options where one has a higher upfront cost but lower ongoing costs:

```
initial_diff = option_a.initial_price - option_b.initial_price
annual_savings = option_b.annual_cost - option_a.annual_cost

break_even_years = initial_diff / annual_savings
```

If `annual_savings ≤ 0`, there is no break-even — the cheaper option stays cheaper forever. State this plainly.

## The 6 Inputs

| Input | What It Means | Example |
|-------|---------------|---------|
| **Initial price** | Upfront purchase or development cost | ¥4,500,000 server, $50,000 dev sprint |
| **Useful life (years)** | How long you'll actually use it | 3 years for SaaS, 7 years for equipment |
| **Residual value** | What you get back at end of life | Trade-in, salvage, resale value |
| **Annual maintenance** | Yearly upkeep, repairs, support contracts | Vendor support, patches, warranty |
| **Annual operating cost** | Ongoing operational expenses | Power, cooling, licences, hosting |
| **Discount rate** | Time value of money adjustment | 0.03 (3%) default |

**Critical distinction:** Initial price is paid once. Maintenance and operating costs are paid every year for the full useful life. A ¥50,000/year maintenance contract on a 10-year asset adds ¥500,000 to the total — often more than people expect.

## Execution Instructions

### Step 1: Identify the Decision

Ask the user what they're comparing. Common patterns:

- **Build vs Buy** — internal development cost vs. SaaS subscription
- **Premium vs Budget** — expensive/durable vs. cheap/disposable
- **Keep vs Replace** — maintaining old equipment vs. buying new
- **Lease vs Own** — recurring payments vs. upfront capital

If they have a single option, calculate its TCO. If they have two or more, compare them.

### Step 2: Collect Inputs

For each option, gather:

1. **Initial price** — what's the upfront cost? (must be ≥ 0)
2. **Useful life** — how many years will you use this? (must be > 0)
3. **Residual value** — what's it worth at end of life? (default: 0)
4. **Annual maintenance** — yearly upkeep costs? (default: 0)
5. **Annual operating cost** — yearly running costs? (default: 0)
6. **Discount rate** — use 3% unless the user specifies otherwise

Help the user uncover hidden costs they might not have considered:

- Training and onboarding costs (add to initial price or first-year operating)
- Migration and integration costs (add to initial price)
- Downtime and productivity loss during transition (add to initial price)
- Licence scaling — does cost grow with team size? (adjust annual operating)
- Context switching overhead — if this tool adds to tool sprawl, that's a real cost

### Step 3: Calculate TCO

For each option, compute all metrics:

```
total_operational = (annual_maintenance + annual_operating_cost) × useful_life_years
total_cost = initial_price + total_operational - residual_value
annual_cost = total_cost / useful_life_years
monthly_cost = annual_cost / 12
daily_cost = annual_cost / 365
```

For NPV:
```
npv_operational = Σ (annual_maintenance + annual_operating_cost) / (1 + discount_rate)^year
npv_residual = residual_value / (1 + discount_rate)^useful_life_years
npv_tco = initial_price + npv_operational - npv_residual
npv_annual = npv_tco / useful_life_years
```

Round all currency values to 2 decimal places.

### Step 4: Compare (if multiple options)

Rank options by **annual cost** (lowest first). Annual cost is the fairest comparison metric because it normalises for different lifespans.

If two options have significantly different lifespans, flag this: "Option A lasts 3 years while Option B lasts 7 — you'll need to replace A more than twice in the same period. Consider the replacement cycle."

### Step 5: Break-Even (if applicable)

If one option has a higher initial price but lower annual cost, calculate the break-even point. This tells the user "the premium pays for itself after X years."

If break-even exceeds the useful life of the cheaper option, state it: "The premium investment doesn't pay off within the planning horizon."

### Step 6: Present Results

**Single option:**

```
=== TCO Analysis ===

Option: Internal Server
Initial price:        ¥4,500,000
Useful life:          7 years
Residual value:       ¥500,000
Annual maintenance:   ¥200,000
Annual operating:     ¥150,000

Simple TCO:
  Total cost:         ¥6,450,000
  Annual cost:        ¥921,429
  Monthly cost:       ¥76,786
  Daily cost:         ¥2,524

NPV-Adjusted (3%):
  NPV TCO:            ¥6,078,231
  NPV annual:         ¥868,319
```

**Comparison:**

```
=== TCO Comparison ===

                    Build In-House      SaaS Subscription
Initial price:      ¥5,000,000          ¥0
Useful life:        5 years             5 years
Annual maintenance: ¥1,000,000          ¥0
Annual operating:   ¥0                  ¥1,800,000

Total cost:         ¥10,000,000         ¥9,000,000
Annual cost:        ¥2,000,000          ¥1,800,000
Monthly cost:       ¥166,667            ¥150,000

Winner by annual cost: SaaS Subscription (¥200,000/year cheaper)
Break-even: N/A — SaaS is cheaper from year 1
```

After presenting, offer interpretation — what does this mean for the decision? What assumptions are most sensitive?

## Worked Examples (Self-Check)

### Worked Example A — Equipment Lifecycle

Inputs:
- Initial price: ¥450,000
- Useful life: 12 years
- Residual value: ¥90,000
- Annual maintenance: ¥5,000
- Annual operating: ¥0
- Discount rate: 3%

**Simple TCO:**
```
Total operational = ¥5,000 × 12 = ¥60,000
Total cost = ¥450,000 + ¥60,000 - ¥90,000 = ¥420,000
Annual cost = ¥420,000 / 12 = ¥35,000
Monthly cost = ¥35,000 / 12 = ¥2,917
Daily cost = ¥35,000 / 365 = ¥95.89
```

**NPV-Adjusted (3%):**
```
NPV operational = ¥5,000/1.03 + ¥5,000/1.03² + ... + ¥5,000/1.03¹² = ¥49,770.02
NPV residual = ¥90,000 / 1.03¹² = ¥63,124.19
NPV TCO = ¥450,000 + ¥49,770.02 - ¥63,124.19 = ¥436,645.83
NPV annual = ¥436,645.83 / 12 = ¥36,387.15
```

### Worked Example B — Build vs Buy (SaaS Comparison)

**Option A — Build In-House:**
- Initial price: ¥5,000,000 (development cost)
- Useful life: 5 years
- Annual maintenance: ¥1,000,000 (internal team)
- Annual operating: ¥0

**Option B — SaaS Subscription:**
- Initial price: ¥0
- Useful life: 5 years
- Annual maintenance: ¥0
- Annual operating: ¥1,800,000 (subscription)

**TCO Comparison:**
```
Option A:
  Total cost = ¥5,000,000 + (¥1,000,000 × 5) - ¥0 = ¥10,000,000
  Annual cost = ¥10,000,000 / 5 = ¥2,000,000

Option B:
  Total cost = ¥0 + (¥1,800,000 × 5) - ¥0 = ¥9,000,000
  Annual cost = ¥9,000,000 / 5 = ¥1,800,000

Winner: Option B (SaaS) — ¥200,000/year cheaper
```

**Break-even:**
```
initial_diff = ¥5,000,000 - ¥0 = ¥5,000,000
annual_savings = ¥1,800,000 - ¥2,000,000 = -¥200,000

annual_savings ≤ 0 → No break-even. SaaS is always cheaper in this scenario.
```

**But that's not the whole story.** TCO says SaaS wins on cost — but what about control, customisation, data ownership, and vendor lock-in? TCO is one input to the decision, not the decision itself. State this.

### Worked Example C — Premium vs Budget (Break-Even Exists)

**Option A — Premium:**
- Initial price: ¥300,000
- Useful life: 10 years
- Annual maintenance: ¥5,000

**Option B — Budget:**
- Initial price: ¥80,000
- Useful life: 3 years
- Annual maintenance: ¥15,000

**TCO Comparison:**
```
Option A:
  Total cost = ¥300,000 + (¥5,000 × 10) = ¥350,000
  Annual cost = ¥350,000 / 10 = ¥35,000

Option B:
  Total cost = ¥80,000 + (¥15,000 × 3) = ¥125,000
  Annual cost = ¥125,000 / 3 = ¥41,667
```

**Winner by annual cost: Premium** — ¥6,667/year cheaper despite 3.75× higher upfront price.

**Break-even:**
```
initial_diff = ¥300,000 - ¥80,000 = ¥220,000
annual_savings = ¥41,667 - ¥35,000 = ¥6,667

break_even = ¥220,000 / ¥6,667 = 33.0 years
```

Break-even at 33 years exceeds both useful lives. **The premium is cheaper per year, but the upfront difference is so large that the savings never recoup it within a single lifecycle.** The user needs to decide: is the lower annual cost worth the higher capital outlay?

Use these examples to verify your calculations are correct before presenting results to the user.

## Hidden Cost Checklist

When a user says "it costs X", probe for what's missing. These are the costs that make TCO different from price:

- **Migration costs** — moving data, retraining staff, parallel running periods
- **Integration costs** — connecting to existing systems, API development, testing
- **Training costs** — onboarding, documentation, learning curve productivity loss
- **Scaling costs** — per-seat licences, usage tiers, storage growth
- **Opportunity cost** — what else could this money or time be spent on?
- **Tool sprawl cost** — if this adds another tool to the stack, factor in context switching overhead (see: PERT's Fragmented Communication tag)
- **Exit costs** — what does it cost to switch away? Data export, contract penalties, knowledge loss

Don't force all of these into every analysis. But if the user is comparing build vs buy, or evaluating a new tool, ask whether they've considered the ones most relevant to their context.

## What This Skill Does NOT Cover

- **NPV as a standalone analysis** — this skill uses NPV to adjust TCO, but doesn't do full capital budgeting. NPV module is planned.
- **IRR (Internal Rate of Return)** — for evaluating investment returns. Planned module.
- **ROI (Return on Investment)** — the capstone that synthesises TCO, NPV, and IRR. Planned module.
- **PERT estimation** — for estimating how long something will take, use the PERT Skill.
- **EVM tracking** — for monitoring cost and schedule performance mid-project, use the EVM Skill.

For programmatic access, scenario persistence, or batch comparisons, point to the API at [github.com/lemur47/logic](https://github.com/lemur47/logic).

## Tone

Be precise and grounded. TCO is about honest numbers, not persuasion. If the cheap option is genuinely cheaper over its lifetime, say so — don't hunt for hidden costs to justify the expensive one. If the expensive option wins on annual cost but loses on break-even, present both facts. The user makes the decision; the Skill provides the math. When hidden costs are genuinely missing from the user's framing, surface them — that's where TCO adds the most value.
