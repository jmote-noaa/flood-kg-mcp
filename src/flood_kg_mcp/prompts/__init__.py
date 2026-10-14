"""Prompts submodule — reusable conversation starters.

Each prompt module exposes a `register(mcp)` function; this file aggregates
them into `register_prompts(mcp)`.
"""

from __future__ import annotations

from flood_kg_mcp.prompts import flood_kg_analyst


def register_prompts(mcp) -> None:
    """Register all prompts with the MCP server."""
    flood_kg_analyst.register(mcp)


__all__ = ["register_prompts"]
