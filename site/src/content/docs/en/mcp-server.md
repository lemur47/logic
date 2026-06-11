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
uvx pmorun-mcp
```

Prefer a persistent install? `uv pip install pmorun-mcp` (or plain `pip install pmorun-mcp`) gives you a `pmorun-mcp` console command.

## Wire It Into Claude

For Claude Code, one line:

```bash
claude mcp add pmo-logic -- uvx pmorun-mcp
```

For Claude Desktop, add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pmo-logic": {
      "command": "uvx",
      "args": ["pmorun-mcp"]
    }
  }
}
```

Restart, and the four tools appear under the `pmo-logic` server.

## Ask a Real Question

Once connected, you stop writing JSON and start asking questions:

> "Here are the three-point estimates for the migration tasks and their dependencies. What completion date can we commit to with 85% confidence, and which tasks should we de-risk first?"

Claude calls `identify_schedule_risk`, runs a seeded Monte Carlo simulation over your task network, and answers with the P85 date and the critical-path frequency per task — numbers you can take into a steering meeting.

## Marketplace Listing Coming Later

A listing in the MCP marketplace is on the roadmap, which will make installation a one-click affair. Until then, PyPI is the canonical channel — `uvx pmorun-mcp` is all you need.

## Going Deeper

The [server README on GitHub](https://github.com/lemur47/logic/blob/main/mcp_server/README.md) covers worked examples for every tool, the structured-error contract, the architecture, and how to run from a source checkout. The package is MIT-licensed, like the rest of the [logic repo](https://github.com/lemur47/logic).
