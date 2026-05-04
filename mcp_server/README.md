# pmo.run MCP Server (Prototype)

An MCP server that exposes the pmo.run **decision-logic** modules — PERT, Monte
Carlo, TCO, EVM — as tools an LLM can call. It is one half of the composition
pattern that makes pmo.run useful: a data-source MCP (Airtable, GitHub) feeds
records in; this server runs the maths; Claude orchestrates and narrates the
result.

> **Status:** prototype. Five tools, stdio transport, light tests. The
> flagship `estimate_from_history` ships at calibration version **v0.1** —
> conservative formulae documented in code, subject to refinement once we
> have field data.

## Why it exists

Without historical data composition, an MCP tool over PERT is just a slow
Airtable formula. The differentiator is composing past actuals + human
judgement + insight tags into a calibrated estimate the LLM can defend. That
is what `estimate_from_history` does, and what the four supporting tools
plug into.

## What's in the box

| Tool | Decision question | Wraps |
|---|---|---|
| `estimate_task_duration` | "How long will this single task take, given a three-point estimate and known frictions?" | `app.pert.core.calculate_task` |
| `estimate_from_history` | "Given past actuals and where we are now, what is a calibrated estimate?" | Layer 2 (history) + `calculate_task` |
| `identify_schedule_risk` | "Across this task network, which tasks drive most of the schedule risk?" | `app.montecarlo.core.simulate_schedule` |
| `compare_investment_options` | "Of these vendor / platform / tool options, which is cheapest on real lifetime cost?" | `app.tco.core.compare_options` |
| `evaluate_project_health` | "Given PV / EV / AC / BAC, are we on track, at risk, or off track?" | `app.evm.core.evm_metrics` + `health_signal` |

Tools are named verb-noun (`estimate_*`, `identify_*`, `compare_*`,
`evaluate_*`), not by acronym (`pert`, `tco`, `evm`). LLMs pick tools by
purpose, not by domain shorthand.

## How it fits into the stack

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude (orchestrator) — composes tools into a decision         │
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

The MCP server depends only on `app.{module}.core` — never on FastAPI, the
SQLite store, or the routers. It runs without uvicorn, without the database,
and stays portable to a future TypeScript port that mirrors the same surface.

## Layer 2 calibration (`estimate_from_history`, v0.1)

Two layers compose into one estimate:

- **Layer 2 (pre-PERT) — history applicability.** Given `past_actuals`,
  `team_familiarity`, `complexity_factor`, and `novelty_factor`, derive the
  most-likely (`derived_M`) and pessimistic (`derived_P`) inputs.
- **Layer 1 (post-PERT) — environmental adjustment.** Apply `insight_tags`
  (e.g. `FRAGMENTED_COMMUNICATION`, `MULTIPLE_STAKEHOLDERS`,
  `HIDDEN_DEPENDENCIES`) on top of the textbook PERT result.

The v0.1 Layer 2 formula:

```
base_M       = median(past_actuals)
base_spread  = max(past_actuals) − base_M       (if ≥ 2 actuals)
             = base_M × 0.3                      (if 1 actual — heuristic)

derived_M    = base_M × (1 + complexity_factor × 0.4)

familiarity_mul = 2.0 − team_familiarity        (∈ [1.0, 2.0])
novelty_mul     = 1 + novelty_factor × 0.5
derived_spread  = base_spread × familiarity_mul × novelty_mul
derived_P       = derived_M + derived_spread
```

The numbers (`0.4`, `0.5`, the familiarity range) are conservative defaults.
They will be tuned against real estimation logs once Bayesian updating has
enough data per task category — at which point Layer 2 calibration knobs
become priors that the system learns over time.

## Running it

Install with the optional `[mcp]` extra:

```bash
uv pip install -e ".[mcp]"
```

Run via stdio (the FastMCP default):

```bash
uv run python -m mcp_server.server
```

Wire it into Claude Desktop by adding this to
`~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)
or the equivalent on Linux/Windows:

```json
{
  "mcpServers": {
    "pmo-logic": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/logic",
        "run",
        "python",
        "-m",
        "mcp_server.server"
      ]
    }
  }
}
```

For Claude Code, use `claude mcp add pmo-logic uv run python -m mcp_server.server`
from the repo root.

## Development

Tests live in `tests/mcp_server/`:

```bash
pytest tests/mcp_server/
```

They cover registration (all five tools present, every tool description
leads with the decision question) and one happy path per tool, plus a
handful of Layer 2 edge cases on the flagship. Implementation-grade test
sweeps for the underlying maths live in `tests/{pert,montecarlo,tco,evm}/`
already — we don't duplicate them here.

## Out of scope (for now)

- **SSE / HTTP transport.** stdio is enough for local Claude Desktop /
  Claude Code wiring. The `mcp[cli]` package supports SSE; flip the
  transport in `server.py` when remote consumers (Make.com, web clients)
  are needed.
- **Persistence.** Tools are stateless. The agent is responsible for
  persisting results back through the data-source MCP.
- **Bayesian wiring.** Once the Bayesian module's posteriors have field
  data, Layer 2 priors will move from hard-coded constants to learned
  parameters.

## Follow-ups

1. **Calibrate Layer 2 against estimation_log data.** Replace the v0.1
   constants with Bayesian-updated priors per task_category.
2. **SSE / HTTP transport.** For the Make.com integration path.
3. **Add `simulate_with_drift` exposure.** The new Sprint 8 Dirichlet-drift
   work in `app.montecarlo.core.simulate_with_drift` would slot naturally
   into `identify_schedule_risk` once we agree on how to expose
   `risk_class` / posteriors via MCP without exploding the tool's input
   surface.

## Licence

MIT — same as the rest of the logic repo.
