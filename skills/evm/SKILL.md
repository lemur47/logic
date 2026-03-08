# EVM: Earned Value Management for Project Health Tracking

> Source: [github.com/lemur47/logic](https://github.com/lemur47/logic)

## Purpose

Help users answer one question: **"Are we on track?"** using Earned Value Management metrics. This skill replaces gut-feel status reporting and traffic-light dashboards with four computed numbers (SV, SPI, CV, CPI) that tell you exactly where a project stands — in schedule and in budget — at any point in time.

EVM is the performance counterpart to PERT. PERT asks "how long will it take?" before the project starts. EVM asks "are we on track?" once it's running.

## When to Use

- Mid-project health checks ("we're 3 months in, are we OK?")
- Sponsor/steering committee reporting with actual data
- Detecting schedule or cost problems before they become crises
- Evaluating whether 人海戦術 (adding headcount) is helping or hurting
- Deciding whether to re-baseline, descope, or extend the deadline
- Any situation where someone says "I think we're roughly on track"

## Terminology — The 4 Inputs

EVM has four inputs. Everything else is computed. Never confuse input with output.

| Abbr | Full Name | What It Means | Who Provides It |
|------|-----------|---------------|-----------------|
| **BAC** | Budget at Completion | Total planned budget for the entire project | Set once at baseline, frozen |
| **PV** | Planned Value | How much work *should* be done by now, in budget terms | Derived from schedule: BAC × (% of schedule elapsed) |
| **EV** | Earned Value | How much work *is actually* done, valued at planned rates | Sum of (planned cost of each completed deliverable × its % complete) |
| **AC** | Actual Cost | What was actually spent on the work performed | From accounting, timesheets, or invoices |

**Critical distinction:** EV is not what was spent. EV is the *planned budget* for the work that's been completed. If a $10,000 deliverable is 50% done, EV = $5,000 regardless of whether you actually spent $3,000 or $8,000 on it.

**PV shortcut (linear assumption):** If you don't have a detailed planned-value curve, use: `PV = BAC × (months elapsed / total months)`. This assumes work is evenly distributed — good enough for most conversational health checks.

## Core Formulas

### Schedule Performance (are we ahead or behind?)

```
Schedule Variance:          SV  = EV - PV
Schedule Performance Index: SPI = EV / PV
```

- SV > 0 or SPI > 1.0 → ahead of schedule
- SV = 0 or SPI = 1.0 → exactly on schedule
- SV < 0 or SPI < 1.0 → behind schedule

**Memory aid:** SPI = 0.80 means "for every $1 of work we planned to finish, we've only finished $0.80 worth."

### Cost Performance (are we under or over budget?)

```
Cost Variance:          CV  = EV - AC
Cost Performance Index: CPI = EV / AC
```

- CV > 0 or CPI > 1.0 → under budget
- CV = 0 or CPI = 1.0 → exactly on budget
- CV < 0 or CPI < 1.0 → over budget

**Memory aid:** CPI = 0.70 means "for every $1 spent, we only got $0.70 of value." Or inversely: every dollar of value is costing us $1.43.

**Pattern for all four:** EV is always the left operand. "S" metrics compare EV to PV (schedule). "C" metrics compare EV to AC (cost).

### Forecasting (where are we heading?)

```
Estimate at Completion:         EAC  = BAC / CPI
Estimate to Complete:           ETC  = EAC - AC
Variance at Completion:         VAC  = BAC - EAC
To-Complete Performance Index:  TCPI = (BAC - EV) / (BAC - AC)
```

- **EAC** — projected total cost if current spending rate continues
- **ETC** — how much more we need to spend to finish
- **VAC** — projected overrun (negative = bad)
- **TCPI** — what CPI must be for remaining work to hit BAC. This is the most actionable metric.

**TCPI interpretation:**
- TCPI ≈ 1.0 → remaining work needs normal efficiency. Achievable.
- TCPI = 1.1–1.2 → remaining work needs above-average efficiency. Challenging.
- TCPI > 1.2 → remaining work needs superhuman efficiency. **This is your re-baseline signal.**

### Progress

```
Percent complete: (EV / BAC) × 100
Percent spent:    (AC / BAC) × 100
```

If percent spent > percent complete, you're spending faster than you're delivering.

## Health Signal

Interpret SPI and CPI into one of three states. Three states, not five — PMOs drown in traffic-light gradients where everything ends up amber.

| Status | Condition | Meaning |
|--------|-----------|---------|
| **On Track** | SPI ≥ 1.0 AND CPI ≥ 1.0 | Schedule and cost within tolerance |
| **At Risk** | SPI 0.9–1.0 OR CPI 0.9–1.0 (neither below 0.9) | Minor deviation, monitor closely |
| **Off Track** | SPI < 0.9 OR CPI < 0.9 | Immediate attention required |

These thresholds follow general PMI/PMBOK guidance. Adjust per project:
- A startup burning VC cash may tolerate CPI = 0.8 temporarily
- A government infrastructure project may flag at CPI = 0.95
- If TCPI > 1.2, the project is off track regardless of SPI/CPI

## Execution Instructions

### Step 1: Establish the Baseline

Ask the user for their project baseline. This is the approved plan — the reference point:

1. **BAC (Budget at Completion)** — total planned budget. Currency or effort-hours.
2. **Work packages** — the major deliverables with their planned cost/effort. These are WBS work packages, not individual tasks. Typical: 3–10 packages for a small project, 10–30 for a large one.
3. **Timeline** — total planned duration (months or weeks).

If the user doesn't have a formal baseline, help them construct one:
- List the major deliverables
- Assign a planned cost or effort to each
- Sum them for BAC
- Note: this is now their baseline. Changing it later means re-baselining.

### Step 2: Capture Current State

Ask for the current snapshot:

1. **How far through the schedule are we?** — e.g. "month 3 of 6" = 50%. This gives PV.
2. **For each work package, what percent is complete?** — be specific. "Auth module is 80% done, API is 30% done." This gives EV.
3. **What has been spent so far?** — total actual cost to date. This is AC.

Compute PV and EV:
```
PV = BAC × (percent of schedule elapsed / 100)
EV = Σ (work_package_planned_cost × percent_complete / 100)
```

### Step 3: Calculate All Metrics

Compute in this order:

```
SV  = EV - PV
SPI = EV / PV
CV  = EV - AC
CPI = EV / AC
EAC = BAC / CPI
ETC = EAC - AC
VAC = BAC - EAC
TCPI = (BAC - EV) / (BAC - AC)
Percent complete = (EV / BAC) × 100
Percent spent = (AC / BAC) × 100
```

Round currency values to 2 decimal places. Round ratios (SPI, CPI, TCPI) to 2–4 decimal places.

**Edge cases:**
- If PV = 0 (schedule hasn't started yet): SPI is undefined. Show "N/A".
- If AC = 0 (no money spent yet): CPI is undefined. Show "N/A".
- If BAC - AC = 0 (entire budget spent): TCPI is undefined. Show "Budget exhausted".
- If CPI = 0 (money spent, no value earned): EAC is undefined. Show "No value earned".

### Step 4: Determine Health Signal

Apply the thresholds:

1. Check SPI against schedule thresholds (0.9 off-track, 1.0 at-risk)
2. Check CPI against cost thresholds (0.9 off-track, 1.0 at-risk)
3. The worse of the two determines overall status
4. If TCPI > 1.2, override to off-track regardless

State the status, the reasons, and one summary sentence.

### Step 5: Present Results

Always present in this structure:

```
=== EVM Health Check ===

BAC: $30,000          (total planned budget)
PV:  $15,000          (what should be done by now)
EV:  $10,100          (what is actually done)
AC:  $14,500          (what has been spent)

Schedule:  SV = -$4,900   SPI = 0.67  → Behind schedule
Cost:      CV = -$4,400   CPI = 0.70  → Over budget

Forecast:  EAC  = $42,857  (projected total cost)
           ETC  = $28,357  (still need to spend)
           VAC  = -$12,857 (projected overrun)
           TCPI = 1.28     (remaining work needs 128% efficiency)

Progress:  33.7% complete, 48.3% spent

Health: OFF TRACK
→ Schedule: SPI 0.67 < 0.9
→ Cost: CPI 0.70 < 0.9
→ TCPI 1.28 > 1.2: re-baseline signal
```

After presenting, offer interpretation:
- What does this mean in plain language?
- What are the options? (re-baseline, descope, extend deadline, accept overrun)
- If 人海戦術 is being considered: show that adding headcount increases AC without proportionally increasing EV, which makes CPI worse.

### Step 6: Work Package Breakdown (if baseline available)

If the user provided work packages, show a per-package breakdown:

```
Work Package              Progress    EV / Planned
Requirements & Design     ████████████████████ 100%    $3,000 / $3,000
Auth Module               ████████████████░░░░  80%    $4,000 / $5,000
API Development           ██████░░░░░░░░░░░░░░  30%    $2,400 / $8,000
Frontend                  ██░░░░░░░░░░░░░░░░░░  10%    $  700 / $7,000
Testing & QA              ░░░░░░░░░░░░░░░░░░░░   0%    $    0 / $4,000
Deployment & Docs         ░░░░░░░░░░░░░░░░░░░░   0%    $    0 / $3,000
```

This makes the bottleneck visible. In the example above: Auth is nearly done, but API and Frontend are dangerously behind, and Testing hasn't started — that's the real problem, not the average.

## Worked Examples (Self-Check)

### Worked Example A — Mid-Project, Off Track

Inputs:
- BAC = $200,000
- Month 6 of 12 → PV = $200,000 × 50% = $100,000
- EV = $80,000 (team has completed work planned at $80K)
- AC = $110,000 (actually spent $110K)

**Metrics:**
```
SV  = 80,000 - 100,000 = -$20,000     (behind schedule)
SPI = 80,000 / 100,000 = 0.80          (20% behind)
CV  = 80,000 - 110,000 = -$30,000     (over budget)
CPI = 80,000 / 110,000 = 0.7273       (27% over budget)
EAC = 200,000 / 0.7273 = $275,000     (projected total)
ETC = 275,000 - 110,000 = $165,000    (still need)
VAC = 200,000 - 275,000 = -$75,000    (projected overrun)
TCPI = (200,000 - 80,000) / (200,000 - 110,000) = 120,000 / 90,000 = 1.3333

Percent complete: 40.0%
Percent spent: 55.0%
```

**Health: OFF TRACK**
- SPI 0.80 < 0.9 (behind schedule)
- CPI 0.73 < 0.9 (over budget)
- TCPI 1.33 > 1.2 (re-baseline signal — remaining work needs 133% efficiency)

**Plain language:** "We're 6 months in but only 40% done, having spent 55% of the budget. At this rate, the project will cost $275K instead of $200K — a $75K overrun. To finish on the original budget, the remaining work would need to be done at 133% cost efficiency, which is unrealistic. Time to re-baseline or descope."

### Worked Example B — Ahead and Under Budget

Inputs:
- BAC = $100,000
- Month 4 of 10 → PV = $100,000 × 40% = $40,000
- EV = $50,000
- AC = $38,000

**Metrics:**
```
SV  = 50,000 - 40,000 = +$10,000      (ahead of schedule)
SPI = 50,000 / 40,000 = 1.25           (25% ahead)
CV  = 50,000 - 38,000 = +$12,000      (under budget)
CPI = 50,000 / 38,000 = 1.3158        (32% under budget)
EAC = 100,000 / 1.3158 = $76,000      (projected total)
ETC = 76,000 - 38,000 = $38,000       (still need)
VAC = 100,000 - 76,000 = +$24,000     (projected savings)
TCPI = (100,000 - 50,000) / (100,000 - 38,000) = 50,000 / 62,000 = 0.8065

Percent complete: 50.0%
Percent spent: 38.0%
```

**Health: ON TRACK**
- SPI 1.25 ≥ 1.0
- CPI 1.32 ≥ 1.0
- TCPI 0.81 < 1.0 (remaining work can be done at lower efficiency and still finish under budget)

### Worked Example C — The 人海戦術 Trap

**Before adding headcount (month 4 of 8):**
```
BAC = $160,000, PV = $80,000, EV = $60,000, AC = $70,000
SPI = 0.75, CPI = 0.857
```

Project is behind. Management adds 3 contractors at $15K/month.

**After one month of additional headcount (month 5 of 8):**
```
PV = $100,000, EV = $78,000, AC = $115,000
SPI = 0.78 (+0.03, barely improved)
CPI = 0.678 (-0.18, significantly worse)
EAC = $235,897 (was $186,667 — overrun increased by $49,231)
TCPI = 1.82 (was 1.11 — now mathematically impossible)
```

**What happened:** The new team added $45K in costs (salaries + onboarding + equipment + meeting overhead) but only produced $18K of earned value. AC jumped faster than EV. CPI collapsed. The "solution" accelerated the problem.

**This is the worked example to show anyone considering 人海戦術.** The math doesn't lie.

Use these three examples to verify your calculations are correct before presenting results to the user.

## Rounding Rules

- Currency values: round to 2 decimal places ($1,234.56)
- Ratios (SPI, CPI, TCPI): round to 2–4 decimal places (0.73 or 0.7273)
- Percentages: round to 1 decimal place (33.7%)
- Present large currency values with thousands separators ($42,857)

## What This Skill Does NOT Cover

- **Baseline persistence** — this skill calculates from inputs provided in conversation. It doesn't save baselines between sessions. For persistent baselines and snapshot history, use the FastAPI API.
- **Non-linear PV curves (S-curves)** — this skill uses the linear PV assumption (BAC × % elapsed). Real projects have S-shaped spending patterns. The linear approximation is honest and sufficient for health checks.
- **Multiple EAC formulas** — we use `BAC / CPI` (assumes current CPI continues). PMI also defines `AC + (BAC - EV)` and bottom-up ETC. Our choice is deliberate — if the user needs alternate forecasts, point them to the API.
- **PERT estimation** — for estimating *before* the project starts, use the PERT Skill.
- **Bayesian updating** — learning from estimation gaps over time. Planned module.

For persistent baselines, snapshot history, or production integration, point to the API at [github.com/lemur47/logic](https://github.com/lemur47/logic).

## Tone

Be direct and clinical. EVM is diagnostic — present the numbers, state the diagnosis, offer the options. Don't soften bad news ("the metrics suggest some concern") — say it plainly ("the project is off track"). If TCPI > 1.2, say "re-baseline signal" not "this might be challenging." PMs and PMOs need clarity, not comfort. The numbers are the evidence — let them speak.
