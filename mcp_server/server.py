"""
pmo.run MCP server (prototype).

Exposes the pure-function `app.{module}.core` layer to MCP clients via
FastMCP over stdio. Designed for composition: an LLM combines these
decision-logic tools with a data-source MCP (e.g. Airtable) to answer
PMO questions an Airtable formula alone cannot.

Run:
    uv run python -m mcp_server.server

License: MIT
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import tools

mcp = FastMCP("pmo-logic")

# Register tools — each is a thin adapter over the corresponding
# app.{module}.core function. See tools.py for implementation.
mcp.tool()(tools.estimate_task_duration)
mcp.tool()(tools.estimate_from_history)
mcp.tool()(tools.identify_schedule_risk)
mcp.tool()(tools.compare_investment_options)
mcp.tool()(tools.evaluate_project_health)


def main() -> None:
    """Entry point for `python -m mcp_server.server` and stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
