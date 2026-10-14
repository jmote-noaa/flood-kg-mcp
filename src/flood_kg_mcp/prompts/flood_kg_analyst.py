"""Prompt: flood_kg_analyst — analyst system instructions for the Texas Flood KG.

Returns the contents of the prompt-guidelines file as a system-role message.
The guidelines cover reasoning principles, SPARQL generation rules, cross-dataset
patterns, county-harmonisation rules, analytical reasoning guidance, and
hallucination-prevention rules.

Agents and clients that support system prompts should apply this before any
query session. Clients that only support user messages receive the same text
framed as context.
"""

from __future__ import annotations

from fastmcp import FastMCP

from flood_kg_mcp.config import settings


def register(mcp: FastMCP) -> None:
    """Register the flood_kg_analyst prompt with the MCP server."""

    @mcp.prompt(name="flood_kg_analyst")
    def flood_kg_analyst() -> str:
        """Analyst system instructions for the Texas Flood Knowledge Graph.

        Returns the full contents of the query-guidelines file, which covers:
          - Reasoning principles and validation rules
          - SPARQL generation rules and query-result formatting
          - Cross-dataset reasoning patterns (flood_exposure, fema_exposure,
            nws_exposure) through shared County entities
          - County harmonisation and reporting rules
          - Analytical reasoning guidance (vulnerability, resilience, exposure)
          - Known graph issues and hallucination-prevention rules

        Load this prompt at the start of a query session to prime the analyst
        with the correct reasoning context. Also read kg://schema for namespace
        prefixes, class definitions, indicator formulas, and common SPARQL
        patterns before writing any query.
        """
        with open(settings.kg_guidelines_path, encoding="utf-8") as fh:
            return fh.read()
