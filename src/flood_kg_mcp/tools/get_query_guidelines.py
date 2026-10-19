"""Tool: kg_get_query_guidelines — return the full kg://query-guidelines YAML.

This tool exists so LangChain-based agents (which load tools but not MCP
resources) can access the analyst guidelines without a separate resource read.
The content is identical to what kg://query-guidelines returns.
"""

from __future__ import annotations

from fastmcp import FastMCP

from flood_kg_mcp.config import settings


def register(mcp: FastMCP) -> None:
    """Register the kg_get_query_guidelines tool with the MCP server."""

    @mcp.tool(
        name="kg_get_query_guidelines",
        annotations={
            "title": "Get Query Guidelines",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kg_get_query_guidelines() -> str:
        """Return the full kg://query-guidelines YAML for the Texas Flood KG.

        Contains reasoning principles, SPARQL generation rules, cross-dataset
        patterns, county harmonisation rules, analytical reasoning guidance,
        known graph issues, and hallucination-prevention rules.

        Read this before writing complex or cross-dataset queries. Equivalent
        to the kg://query-guidelines MCP resource.
        """
        with open(settings.kg_guidelines_path, encoding="utf-8") as fh:
            return fh.read()
