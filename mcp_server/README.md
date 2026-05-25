# pmo.run MCP Server

An MCP server that exposes the pmo.run **decision-logic** modules — PERT, Monte
Carlo, TCO and EVM — as tools an LLM can call. It is one half of the composition
pattern that makes pmo.run useful: a data-source MCP (Airtable, GitHub) feeds
records in; this server runs the maths; Claude orchestrates and narrates the
result.

> **Status: v0.1.** Four classic PMO tools, stdio transport, structured errors.
> Run it from a source checkout (see [Install](#install)); a published package is
> planned for a later release. The hosted lane (Streamable HTTP + auth) and the
> calibration-driven tools are parked for v0.2 — see [Out of scope](#out-of-scope-v02).

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

Until a package is published, run the server from a source checkout:

```bash
git clone https://github.com/lemur47/logic.git
cd logic
uv run python -m mcp_server.server
```

## Wire it into Claude Desktop

Add this to `claude_desktop_config.json` (on macOS,
`~/Library/Application Support/Claude/claude_desktop_config.json`; the path
differs on Linux/Windows), pointing at your checkout:

```json
{
  "mcpServers": {
    "pmo-logic": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/logic", "run", "python", "-m", "mcp_server.server"]
    }
  }
}
```

Restart Claude Desktop; the four tools appear under the `pmo-logic` server.

For Claude Code:

```bash
claude mcp add pmo-logic -- uv --directory /absolute/path/to/logic run python -m mcp_server.server
```

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

They cover registration (exactly the four tools, each leading with a decision
question, each exposing input and output schemas), one worked example per tool,
seed-42 determinism on the Monte Carlo tool, and the structured-error contract.
Implementation-grade maths sweeps live in `tests/{pert,montecarlo,tco,evm}/`
already — we do not duplicate them here.

## Out of scope (v0.2+)

- **Streamable HTTP transport, OAuth, hosting, rate limiting, audit logging** —
  the paid hosted lane. v0.1 is stdio-only and local-trust.
- **Calibration-driven and stochastic-mix tools** — `estimate_from_history`
  (two-layer calibration) is parked in `tools.py`; the Bayesian and
  Dirichlet-drift tools are parked too. All wait on field data to ground their
  calibration before they meet the v0.1 quality bar.

## Licence

MIT — same as the rest of the logic repo.
