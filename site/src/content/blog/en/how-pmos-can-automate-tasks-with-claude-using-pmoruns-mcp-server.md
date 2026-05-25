---
title: "How PMOs Can Automate Tasks With Claude Using pmo.run's MCP Server"
description: "pmo.run's MCP server brings four classic PMI tools — PERT, EVM, TCO, and Monte Carlo schedule — to Claude. A worked example with insight tags."
pubDate: 2026-05-25
tags: ["mcp", "claude", "pert", "pmo", "release"]
contentType: "how-to"
---

[The Hidden Tax on Status Reports](https://pmo.run/en/blog/the-hidden-tax-on-status-reports/) showed why programme communication overhead inflates every delivery estimate. This post is the practical follow-on: pmo.run now ships an MCP server giving Claude four classic PMI tools — PERT, EVM, TCO, and Monte Carlo schedule — installable from source today, with a polished PyPI release on the roadmap. The worked example below shows why a vendor's textbook 14-day estimate often becomes a 28-day programme commit, once you account for friction your vendor cannot see from their side.

## What Does pmo.run's MCP Server Do?

Four PMI tools, each a textbook method wrapped for LLM use, available to any client speaking the MCP stdio protocol — Claude Desktop, Claude Code, or others.

| Tool | Method | Use Case |
|---|---|---|
| `estimate_task_duration` | PERT (three-point estimation) | Single task or activity duration |
| `evaluate_project_health` | EVM (earned value management) | Schedule and cost performance to date |
| `compare_investment_options` | TCO (total cost of ownership) | Multi-year cost comparison across options |
| `identify_schedule_risk` | Monte Carlo schedule simulation | Programme-level risk and percentile dates |

What the server contributes: making these methods reliably callable by Claude with one-line precision and consistent output schemas. Claude computes exact values via the tools rather than estimating numerically — which large language models do poorly without help.

## How Do I Install It?

Tech-savvy installation today, from source:

```bash
git clone https://github.com/lemur47/logic.git
cd logic
uv run python -m mcp_server.server
```

The first `uv run` syncs dependencies and starts the server in stdio mode (Ctrl+C to stop). Everything runs locally — no telemetry, no data leaves your machine.

A `pip install pmorun-mcp` path via PyPI is on the roadmap. The maths is stable today; only the install path will change.

## How Do I Connect It to Claude?

Claude Desktop reads its MCP config from `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows). Add one entry, pointing at your local clone:

```json
{
  "mcpServers": {
    "pmo-logic": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/logic", "python", "-m", "mcp_server.server"]
    }
  }
}
```

Replace `/absolute/path/to/logic` with the directory you cloned into. Restart Claude Desktop; the four tools become available in any conversation.

If you're on Linux or prefer the terminal, Claude Code speaks the same MCP stdio protocol:

```bash
claude mcp add pmo-logic -- uv run --directory /absolute/path/to/logic python -m mcp_server.server
```

The tools work identically — no functional difference between the two clients.

## Worked Example: How Realistic Is Your Vendor's Estimate?

A software vendor's PM gives you a three-point estimate for a custom API integration: 7 / 14 / 21 working days. You're tempted to commit on the textbook 95% upper bound — about 19 days. But your programme has two known frictions:

- The vendor sits in a different timezone (fragmented communication).
- Their integration touches a legacy reporting system whose downstream consumers nobody has mapped (hidden dependencies).

**Step 1: textbook PERT.** Ask Claude to call `estimate_task_duration(O=7, M=14, P=21)`:

| Stat | Formula | Value |
|---|---|---|
| Expected | (O + 4M + P) / 6 | 14 |
| Std deviation | (P − O) / 6 | 2.33 |
| 95% upper bound | E + 2σ | 18.67 |

The symmetric inputs collapse to the most-likely value: 14 days expected, 19-day commit at 95% confidence.

**Step 2: layer the friction.** Re-call with two insight tags applied:

```python
estimate_task_duration(
    optimistic=7, most_likely=14, pessimistic=21,
    tags=[("FRAGMENTED_COMMUNICATION", 0.8),
          ("HIDDEN_DEPENDENCIES", 0.5)]
)
```

The output shifts:

| Stat | Textbook | Adjusted |
|---|---|---|
| Expected | 14 | **16.96** |
| 95% upper bound | 18.67 | **27.55** |
| Combined multiplier | 1.0 | 1.846 |

Your commit date moves from textbook 19 days to programme-reality 28 days. The vendor isn't wrong; they're estimating from their side, where neither friction is visible. The PMO's job is to apply the friction layer the vendor cannot.

## Are the Insight Tag Coefficients Field-Calibrated?

Honest answer: not yet.

What ships in v0.1 is the *mechanism* — three insight tags (`FRAGMENTED_COMMUNICATION`, `HIDDEN_DEPENDENCIES`, `MULTIPLE_STAKEHOLDERS`), each with placeholder multiplier ranges. Severity in `[0, 1]` linearly interpolates each tag's range; tags compose multiplicatively on the pessimistic leg only. The optimistic and most-likely values are untouched — only the tail widens.

The coefficients are sensible PMO defaults, not field-derived. A 42% multiplier from `FRAGMENTED_COMMUNICATION` at severity 0.8 isn't drawn from a dataset of real vendor estimates; it's PMO judgement encoded as a starting point.

What's coming in v0.2: industry-specific calibration via the `plugins/` layer, with multiplier ranges derived from real programme data per sector (financial services, manufacturing, public sector). That work needs an `estimation_log` data source, which is exactly what the proprietary calibration layer is for.

If you're using v0.1 today, treat the adjusted estimate as a *prompt for a sharper conversation with your sponsor*, not as a calibrated commitment. The mechanism is right; the coefficients will sharpen.

## What's Not in v0.1?

Six things deferred to v0.2 and beyond:

- **PyPI release** — public package install (`pip install pmorun-mcp`); needs trusted-publisher setup as a one-time investment.
- **Bayesian estimation** — layer 2 calibration needs field data first.
- **Dirichlet-MC simulation** — same dependency on field data.
- **Hosted Streamable HTTP transport** — v0.1 is local stdio only.
- **OAuth 2.1 authentication** — paired with the hosted transport.
- **Field-calibrated insight tag coefficients** — the proprietary calibration layer, as above.

The local OSS package will continue receiving maths and tooling updates. A hosted, paid version will arrive when the data layer and calibration are ready.

---

Clone the repo and try it on a real estimate. Source: [github.com/lemur47/logic](https://github.com/lemur47/logic). Issues and PRs welcome.
