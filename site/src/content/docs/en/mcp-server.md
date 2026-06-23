---
title: "MCP Server"
description: "Classic PMO decision tools — PERT, Monte Carlo, TCO and EVM — as tools Claude can call. One command to install: uvx pmorun-mcp."
order: 2
---

## What Is the MCP Server?

`pmorun-mcp` exposes the pmo.run decision-logic modules — PERT, Monte Carlo, TCO and EVM — as tools an LLM can call over the [Model Context Protocol](https://modelcontextprotocol.io/). Connect it to Claude alongside your data sources (Airtable, GitHub, spreadsheets) and Claude can pull real project records, run the maths, and narrate the result — instead of guessing at arithmetic.

The maths is the same MIT-licensed core that powers the [Logic API](/en/docs/api-overview/): one source of truth, validated by the same models.

## The Four Tools

Tools are named by the decision they answer, not by acronym — so Claude picks them by purpose.

| Tool | Decision question |
|------|-------------------|
| `estimate_task_duration` | How long will this task take, given a three-point estimate and known frictions? |
| `identify_schedule_risk` | Across this task network, how long are we likely to take — and which tasks drive the risk? |
| `compare_investment_options` | Of these vendor or platform options, which is cheapest on real lifetime cost? |
| `evaluate_project_health` | Given PV / EV / AC / BAC, are we on track, at risk, or off track? |

## Install

The quickest path runs the server without installing anything permanent — `uvx` fetches [`pmorun-mcp` from PyPI](https://pypi.org/project/pmorun-mcp/) into a throwaway environment:

```bash
uvx pmorun-mcp           # latest release
uvx pmorun-mcp@0.1.1     # pinned to this release (recommended)
```

Pinning to `@0.1.1` gives a reproducible install from the immutable PyPI artefact; drop the pin to track the latest.

Prefer a persistent install? `uv pip install "pmorun-mcp==0.1.1"` (or plain `pip install "pmorun-mcp==0.1.1"`) gives you a `pmorun-mcp` console command.

## Wire It Into Claude

For Claude Code, one line:

```bash
claude mcp add pmo-logic -- uvx pmorun-mcp@0.1.1   # or drop @0.1.1 to track latest
```

For Claude Desktop, add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pmo-logic": {
      "command": "uvx",
      "args": ["pmorun-mcp@0.1.1"]
    }
  }
}
```

Restart, and the four tools appear under the `pmo-logic` server.

## Ask a Real Question

Once connected, you stop writing JSON and start asking questions. Start with a single task:

> "The data migration is 2 days best case, 5 days typical, 14 if the legacy schema fights back. What should I plan for?"

Claude calls `estimate_task_duration`, which runs the PERT maths over your three points and answers with an expected duration of **6.0 days** (standard deviation 2.0) — a single, defensible number instead of a gut feel.

Then widen to the whole plan:

> "Here are the three-point estimates for all the migration tasks and their dependencies. What completion date can we commit to with 85% confidence, and which tasks should we de-risk first?"

Claude calls `identify_schedule_risk`, which runs a seeded Monte Carlo simulation across the task network, and answers with the P85 date and each task's critical-path frequency — numbers you can take into a steering meeting.

That is the working pattern: PERT for one task, Monte Carlo for the network of them.

## Marketplace Listing Coming Later

A listing in the MCP marketplace is on the roadmap, which will make installation a one-click affair. Until then, PyPI is the canonical channel — `uvx pmorun-mcp` is all you need.

## Going Deeper

The [server README on GitHub](https://github.com/lemur47/logic/blob/main/mcp_server/README.md) covers worked examples for every tool, the structured-error contract, the architecture, and how to run from a source checkout. The package is MIT-licensed, like the rest of the [logic repo](https://github.com/lemur47/logic).
