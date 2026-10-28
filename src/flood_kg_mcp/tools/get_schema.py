"""Tool: kg_get_schema — return the full kg://schema YAML as a tool response.

This tool exists so LangChain-based agents (which load tools but not MCP
resources) can access the schema without a separate resource read call.
The content is identical to what kg://schema returns.
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from flood_kg_mcp.config import settings

_log = logging.getLogger(__name__)


def register(mcp: FastMCP) -> None:
    """Register the kg_get_schema tool with the MCP server."""

    @mcp.tool(
        name="kg_get_schema",
        output_schema=None,
        annotations={
            "title": "Get KG Schema",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kg_get_schema() -> dict:
        """Return the full KG schema YAML for the Texas Flood Knowledge Graph.

        Contains namespaces, dataset classes, primary relationships, property
        lists, analytical concepts with indicator formulas, analytical constructs
        (vulnerability, resilience, exposure, recovery_capacity), and common
        SPARQL graph paths.

        Call this before writing any SPARQL query. Equivalent to the
        kg://schema MCP resource.
        """
        _log.info("tool=kg_get_schema")
        with open(settings.kg_schema_path, encoding="utf-8") as fh:
            return {"content": fh.read()}
