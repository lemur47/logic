"""
pmo.run MCP server (v0.1).

Exposes the pure-function ``app.{module}.core`` layer to MCP clients via FastMCP
over stdio. Designed for composition: an LLM combines these decision-logic tools
with a data-source MCP (e.g. Airtable) to answer PMO questions a spreadsheet
formula alone cannot.

v0.1 ships four classic PMO tools — PERT, Monte Carlo (schedule), TCO and EVM.
stdio transport only; no auth, no hosting (those are the v0.2 hosted lane).

Run:
    uv run python -m mcp_server.server     # from a source checkout
    pmorun-mcp                             # once installed from PyPI

License: MIT
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import tools

mcp = FastMCP("pmo-logic")

# Register the four v0.1 tools — each a thin adapter over the corresponding
# app.{module}.core function, with shared Pydantic models in and out. See
# tools.py for implementations. `estimate_from_history` is intentionally not
# registered for v0.1 (parked — see the banner in tools.py).
mcp.tool()(tools.estimate_task_duration)
mcp.tool()(tools.identify_schedule_risk)
mcp.tool()(tools.compare_investment_options)
mcp.tool()(tools.evaluate_project_health)


def main() -> None:
    """Entry point for ``python -m mcp_server.server``, the ``pmorun-mcp`` script,
    and stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
