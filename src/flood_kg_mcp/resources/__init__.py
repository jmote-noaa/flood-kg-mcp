"""Resources submodule — static/semi-static data the client can read directly.

Resources are addressable by URI and don't require a tool call. Each resource
module exposes a `register(mcp)` function; this file aggregates them into
`register_resources(mcp)`.
"""

from __future__ import annotations

from flood_kg_mcp.resources import query_guidelines, schema


def register_resources(mcp) -> None:
    """Register all resources with the MCP server."""
    schema.register(mcp)
    query_guidelines.register(mcp)


__all__ = ["register_resources"]
