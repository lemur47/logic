# pmo.run MCP Server

An MCP server that exposes the pmo.run **decision-logic** modules — PERT, Monte
Carlo, TCO and EVM — as tools an LLM can call. It is one half of the composition
pattern that makes pmo.run useful: a data-source MCP (Airtable, GitHub) feeds
records in; this server runs the maths; Claude orchestrates and narrates the
result.

> **Status: v0.1.** Four classic PMO tools, stdio transport, structured errors,
> plus an **opt-in calibration memory** (a local SQLite estimation log — see
> [Calibration memory](#calibration-memory-opt-in)). Published to PyPI as
> [`pmorun-mcp`](https://pypi.org/project/pmorun-mcp/) — install it or run it
> from a source checkout (see [Install](#install)). The hosted lane (Streamable
> HTTP + auth) is parked for v0.2 — see [Out of scope](#out-of-scope-v02).

## What's in the box

Each tool is a thin adapter over the corresponding `app.{module}.core` function,
with inputs and outputs validated by the **same Pydantic models as the FastAPI
surface** — one source of truth, no duplication.

| Tool | Decision question | Wraps |
|---|---|---|
| `estimate_task_duration` | "How long will this single task take, given a three-point estimate and known frictions?" | `app.pert.core.calculate_task` |
| `identify_schedule_risk` | "Across this task network, how long are we likely to take and which tasks drive the risk?" | `app.montecarlo.core.simulate_schedule` |
| `compare_investment_options` | "Of these vendor / platform / tool options, which is cheapest on real lifetime cost?" | `app.tco.core.compare_options` |
| `evaluate_project_health` | "Given PV / EV / AC / BAC, are we on track, at risk, or off track?" | `app.evm.core.evm_metrics` + `health_signal` |

Tools are named verb-noun (`estimate_*`, `identify_*`, `compare_*`,
`evaluate_*`), not by acronym. LLMs pick tools by purpose, not by domain
shorthand — so every description leads with a "Use when:" decision question,
documents every parameter, and states the units of every output.

## How it fits into the stack

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude (orchestrator) — composes tools into a decision          │
└──────────────┬──────────────────────────┬───────────────────────┘
               │                          │
   ┌───────────▼───────────┐  ┌───────────▼───────────┐
   │  Data MCP (Airtable,  │  │  pmo-logic MCP        │
   │  GitHub, etc.)        │  │  (this server)        │
   └───────────────────────┘  └───────────┬───────────┘
                                          │ imports
                                          │ pure-function core
                              ┌───────────▼───────────┐
                              │  app.{module}.core    │
                              │  (MIT-licensed maths) │
                              └───────────────────────┘
```

The server imports only `app.{module}.core` — never the routers or the SQLite
store directly — so it runs without uvicorn or a database, and stays portable to
a future TypeScript port that mirrors the same surface.

## Install

The package is on PyPI as [`pmorun-mcp`](https://pypi.org/project/pmorun-mcp/). The
quickest path is to run it without installing — `uvx` fetches it into a throwaway
environment:

```bash
uvx pmorun-mcp           # latest release
uvx pmorun-mcp@0.2.0     # pinned to this release (recommended)
```

The pinned form (`@0.2.0`) resolves to an immutable PyPI artefact: a reproducible
install that won't be auto-pulled onto a future top-level release. Drop the pin to
always track the latest.

Or install it into an environment of your own:

```bash
uv pip install "pmorun-mcp==0.2.0"   # or: pip install "pmorun-mcp==0.2.0"
pmorun-mcp                           # console script — same entry point as python -m mcp_server.server
```

To hack on the server itself, run it from a source checkout instead:

```bash
git clone https://github.com/lemur47/logic.git
cd logic
uv run python -m mcp_server.server
```

## Wire it into Claude Desktop

Add this to `claude_desktop_config.json` (on macOS,
`~/Library/Application Support/Claude/claude_desktop_config.json`; the path
differs on Linux/Windows):

```json
{
  "mcpServers": {
    "pmo-logic": {
      "command": "uvx",
      "args": ["pmorun-mcp@0.2.0"]
    }
  }
}
```

Pinning the args to `pmorun-mcp@0.2.0` is recommended; use `["pmorun-mcp"]` to
track the latest release instead. Restart Claude Desktop; the four classic tools
appear under the `pmo-logic` server — plus four more if you set `PMORUN_DB`, as
described under *Calibration memory* below.

For Claude Code:

```bash
claude mcp add pmo-logic -- uvx pmorun-mcp@0.2.0   # or drop @0.2.0 to track latest
```

> Running from a source checkout instead? Swap the command for
> `uv --directory /absolute/path/to/logic run python -m mcp_server.server`.

## Worked examples

One representative call per tool. Inputs are the shared Pydantic models, so these
shapes match the FastAPI request bodies exactly.

### `estimate_task_duration` (PERT)

A task estimated at 2 / 5 / 14 (optimistic / most-likely / pessimistic) days:

```json
{ "task": { "optimistic": 2, "most_likely": 5, "pessimistic": 14 } }
```

Returns the textbook PERT expected duration of **6.0** days (`(2 + 4·5 + 14) / 6`)
with a standard deviation of **2.0** (`(14 − 2) / 6`). Add insight tags to widen
the pessimistic tail for known frictions:

```json
{
  "task": {
    "optimistic": 2, "most_likely": 5, "pessimistic": 14,
    "tags": [{ "name": "FRAGMENTED_COMMUNICATION", "severity": 0.5 }]
  }
}
```

### `identify_schedule_risk` (Monte Carlo)

A three-task chain (Design → Build → Test), 2,000 iterations, seeded for
reproducibility:

```json
{
  "tasks": [
    { "name": "Design", "optimistic": 3, "most_likely": 5, "pessimistic": 10 },
    { "name": "Build", "optimistic": 8, "most_likely": 14, "pessimistic": 25, "depends_on": ["Design"] },
    { "name": "Test", "optimistic": 3, "most_likely": 5, "pessimistic": 10, "depends_on": ["Build"] }
  ],
  "config": { "num_simulations": 2000, "seed": 42 }
}
```

Returns P50 ≈ **25.5** and P85 ≈ **29.6** days, plus the per-task
`critical_path_frequency` (in this strict chain, 1.0 for every task — they all
always sit on the critical path). `seed` defaults to **42** when omitted, so runs
are reproducible by default; pass a different integer to vary the draw.

### `compare_investment_options` (TCO)

Cloud (low upfront, high running cost) versus on-prem (high upfront, low running
cost), each over three years:

```json
{
  "request": {
    "options": [
      { "name": "Cloud", "initial_price": 5000, "useful_life_years": 3, "annual_operating_cost": 12000 },
      { "name": "On-prem", "initial_price": 40000, "useful_life_years": 3, "annual_maintenance": 3000 }
    ]
  }
}
```

Returns the options ranked by annual cost (rank 1 = cheapest). Here `best_option`
is **Cloud** (≈ 13,667/yr versus ≈ 16,333/yr for on-prem).

### `evaluate_project_health` (EVM)

A project a little behind and over budget:

```json
{ "evm": { "pv": 1000, "ev": 900, "ac": 1100, "bac": 5000 } }
```

Returns SPI **0.9**, CPI **≈ 0.82**, the forecast `eac`/`etc`/`vac`/`tcpi`, and a
health verdict of **off_track** with the reasons spelled out.

## Calibration memory (opt-in)

By default the server is fully stateless — nothing is written anywhere, and the
four tools above are the whole surface. Set the `PMORUN_DB` environment variable
to a writable file path and four more tools register, backed by a **local SQLite
estimation log**:

```jsonc
// Claude Desktop / claude mcp add — opt in via env
{
  "command": "uvx",
  "args": ["pmorun-mcp"],
  "env": { "PMORUN_DB": "/path/to/calibration.db" }
}
```

> **The database is stored unencrypted.** It is a plain local SQLite file, and
> the task names, categories and estimates you record are readable by anything
> that can read that path. Choose a location covered by your existing disk
> encryption and file permissions, and treat it as you would any other working
> file — do not point `PMORUN_DB` at a shared or synced directory if the task
> names themselves are sensitive.

| Tool | Decision question | Wraps |
|---|---|---|
| `record_estimate` | "Log this three-point estimate so we can learn from it later." | `app.pert.core.calculate_task` + the log |
| `record_actual` | "The task is done — what did it actually take, and how wrong were we?" | the log |
| `summarise_calibration` | "How biased are our estimates, and what should this new estimate really be?" | `app.bayesian.core.update_belief` / `adjust_estimate` |
| `estimate_from_history` | "Given what similar tasks actually took, how long will this one take?" | the two-layer estimator in `tools.py`, grounded in the log |

The loop: `record_estimate` when you commit to an estimate → `record_actual`
when the task completes → `summarise_calibration` learns the systematic delay
factor from every completed pair via conjugate Bayesian updating (prior
N(1.0, 0.25)); pass it a fresh `pert_expected` and it returns the
bias-adjusted estimate with credible intervals. `estimate_from_history` — parked
since v0.1 pending exactly this data source — reads the recorded actuals per
task category and derives a calibrated three-point estimate from them.

Estimates are unit-agnostic (record the `unit`; "sessions", "days" and "hours"
are all fine — the log stores, it never converts). The schema is deliberately
**D1-portable** (plain SQLite DDL, ISO-8601 text timestamps): the local log is
the reference data model for the hosted calibration memory.

Privacy note: the log is a plain local file you own. Nothing leaves the
machine; delete the file and the memory is gone.

## Errors

Every tool returns **structured, tagged errors** — never a Python traceback.
Errors carry a type tag the model can reason about:

- `[ValidationError]` — inputs are individually valid but jointly inconsistent
  (e.g. an unknown insight tag), or rejected before computation.
- `[ComputationError]` — the underlying maths rejected the inputs (e.g. an
  optimistic estimate larger than the most-likely one, a non-positive budget).
- `[InternalError]` — an unexpected failure, reported generically so no internal
  state leaks.

Field-level constraints (a negative cost, fewer than two options to compare) are
caught by the shared Pydantic models and surfaced as structured validation
messages.

## Development

Tests live in `tests/mcp_server/`:

```bash
pytest tests/mcp_server/
```

They cover registration (exactly the four tools by default; the calibration
tools join only when `PMORUN_DB` is set), one worked example per tool, seed-42
determinism on the Monte Carlo tool, the calibration round-trip and its Bayesian
summary maths, and the structured-error contract. Implementation-grade maths
sweeps live in `tests/{pert,montecarlo,tco,evm,bayesian}/` already — we do not
duplicate them here.

## Out of scope for this package

- **Streamable HTTP transport, OAuth, hosting, rate limiting, audit logging** —
  the paid hosted lane, which is a **separate product rather than a later version
  of this package**. `pmorun-mcp` is stdio-only and local-trust by design, and no
  future release of it changes that.
- **Stochastic-mix tools** — the Dirichlet-drift tools remain parked, waiting
  on field data to ground their calibration. (`estimate_from_history` and the
  Bayesian calibration summary shipped with the opt-in calibration memory —
  their data-source precondition is now met by the estimation log.)

## Licence

MIT — same as the rest of the logic repo.
