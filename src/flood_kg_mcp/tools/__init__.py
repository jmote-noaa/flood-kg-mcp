"""Tools submodule — one tool per file.

Each tool module exposes a `register(mcp)` function that attaches its
@mcp.tool-decorated function to the server. This file aggregates them into a
single `register_tools(mcp)` that `app.py` calls.

To add a tool:
  1. Create `tools/<your_tool>.py` with a `register(mcp)` function.
  2. Import it below and call `<your_tool>.register(mcp)` inside register_tools.
"""

from __future__ import annotations

from flood_kg_mcp.tools import (
    list_classes,
    list_predicates_for_class,
    run_sparql,
    sample_instances,
)


def register_tools(mcp) -> None:
    """Register all tools with the MCP server."""
    list_classes.register(mcp)
    list_predicates_for_class.register(mcp)
    sample_instances.register(mcp)
    run_sparql.register(mcp)


__all__ = ["register_tools"]
