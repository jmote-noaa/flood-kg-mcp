"""Resource: kg://query-guidelines — analyst prompt guidelines for the Texas Flood KG.

Exposes the same guidelines file used by the flood_kg_analyst prompt as an
addressable resource, so agents that prefer to read resources directly (rather
than loading a prompt) can access the full analyst context.
"""

from __future__ import annotations

from fastmcp import FastMCP

from flood_kg_mcp.config import settings


def register(mcp: FastMCP) -> None:
    """Register the kg://query-guidelines resource with the MCP server."""

    @mcp.resource("kg://query-guidelines", mime_type="application/yaml")
    def kg_query_guidelines() -> str:
        """Analyst prompt guidelines for the Texas Flood Knowledge Graph.

        Contains the full reasoning context for query sessions, including:
          - Reasoning principles and namespace rules
          - Query-development workflow (inspect schema, build paths, analyse)
          - SPARQL generation rules and result-formatting conventions
          - Cross-dataset reasoning patterns through shared County entities
          - County harmonisation and reporting rules (prefer county names,
            avoid raw URIs, map NWS UGC codes to FIPS)
          - Analytical reasoning guidance for vulnerability, resilience,
            and exposure analyses
          - Known graph issues (county artifacts, NWS coverage gaps)
          - Hallucination-prevention rules (no unsupported composite indices)

        Pair with kg://schema, which provides namespaces, class definitions,
        indicator formulas, and ready-to-use SPARQL triple patterns.
        """
        with open(settings.kg_guidelines_path, encoding="utf-8") as fh:
            return fh.read()
