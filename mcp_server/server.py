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

from . import storage, tools

mcp = FastMCP("pmo-logic")

# Register the four v0.1 tools — each a thin adapter over the corresponding
# app.{module}.core function, with shared Pydantic models in and out. See
# tools.py for implementations.
mcp.tool()(tools.estimate_task_duration)
mcp.tool()(tools.identify_schedule_risk)
mcp.tool()(tools.compare_investment_options)
mcp.tool()(tools.evaluate_project_health)

# Opt-in calibration memory: four more tools, registered ONLY when PMORUN_DB
# points at a local SQLite log. Without the variable the server stays fully
# stateless and the tool list above is the whole surface. This flag is also
# what un-parks `estimate_from_history` — its re-enablement condition (an
# estimation_log data source) is met exactly when the log exists.
if storage.db_path() is not None:
    from . import calibration_tools

    mcp.tool()(calibration_tools.record_estimate)
    mcp.tool()(calibration_tools.record_actual)
    mcp.tool()(calibration_tools.summarise_calibration)
    mcp.tool()(calibration_tools.estimate_from_history)


def main() -> None:
    """Entry point for ``python -m mcp_server.server``, the ``pmorun-mcp`` script,
    and stdio transport."""
    mcp.run()


if __name__ == "__main__":
    main()
