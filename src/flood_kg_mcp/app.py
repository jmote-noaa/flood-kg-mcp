"""MCP server entry point.

Keep this file THIN. It only:
  1. creates the FastMCP instance,
  2. registers tools / prompts / resources / routes from the submodules,
  3. warms the KG store (fail-fast on a bad data path), and
  4. decides which transport to run (stdio locally vs. HTTP when deployed).

All real logic lives in the submodules:
  - tools/      one file per tool (each exposes `register(mcp)`)
                kg_get_schema, kg_get_query_guidelines — schema/guidelines as
                tools so LangChain-based agents can access them without reading
                MCP resources
  - prompts/    flood_kg_analyst — analyst system instructions
  - resources/  kg://schema — KG schema and query guidance
               kg://query-guidelines — analyst reasoning and SPARQL rules
  - routes.py   HTTP-only infrastructure (health check, etc.)
  - config.py   settings loaded from env vars / .env
  - utils.py    shared helpers (KG store, HTTP client, pagination)
"""

from __future__ import annotations

import logging
import os
import sys

from fastmcp import FastMCP

from flood_kg_mcp.config import settings
from flood_kg_mcp.prompts import register_prompts
from flood_kg_mcp.resources import register_resources
from flood_kg_mcp.routes import register_routes
from flood_kg_mcp.tools import register_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stderr,
)

mcp = FastMCP(
    name="Flood Knowledge Graph MCP Server",
    instructions=(
        "This server exposes the Texas Flood Knowledge Graph — an integrated "
        "dataset covering NOAA Storm Events, FEMA Disaster Declarations, "
        "ACS demographic/economic indicators, and NWS flash flood warnings for "
        "Texas counties.\n\n"
        "Before writing any SPARQL query, call both tools to load the schema\n"
        "and guidelines:\n"
        "  kg_get_schema           — namespaces, classes, relationships,\n"
        "                            indicator formulas, analytical constructs\n"
        "                            (vulnerability, resilience, exposure), and\n"
        "                            common graph paths with SPARQL patterns.\n"
        "  kg_get_query_guidelines — analyst reasoning principles, SPARQL\n"
        "                            generation rules, cross-dataset patterns,\n"
        "                            county rules, hallucination prevention.\n"
        "Clients that can read MCP resources may also use kg://schema and\n"
        "kg://query-guidelines directly — both return identical content.\n\n"
        "Load the flood_kg_analyst prompt to prime a full analyst session.\n\n"
        "Available tools:\n"
        "  kg_get_schema                 — full schema YAML (classes, formulas)\n"
        "  kg_get_query_guidelines       — full analyst guidelines YAML\n"
        "  kg_list_classes               — list all RDF classes with instance counts\n"
        "  kg_list_predicates_for_class  — list predicates for a given class URI\n"
        "  kg_sample_instances           — fetch sample instances with all properties\n"
        "  kg_run_sparql                 — run a SELECT or ASK query (200-row cap)\n\n"
        "Default SPARQL prefixes (kg:, flood:, rdf:, rdfs:, xsd:) are injected "
        "automatically by kg_run_sparql for any prefix not declared in your query."
    ),
)

# Wire up everything the server exposes.
register_tools(mcp)
register_prompts(mcp)
register_resources(mcp)
register_routes(mcp)

# Warm the store at import time so a missing or malformed data file raises
# immediately rather than on the first tool call.
from flood_kg_mcp.utils import get_store  # noqa: E402

get_store()


def main() -> None:
    """Start the server, choosing a transport based on the environment.

    Precedence:
      1. A platform-injected port (Databricks `DATABRICKS_APP_PORT` or a generic
         `PORT`) -> run HTTP on that port. Cloud hosts set this for you.
      2. `MCP_TRANSPORT=streamable-http` in the environment -> run HTTP on
         `MCP_HOST`:`MCP_PORT` (see config.py / .env).
      3. Otherwise -> stdio, which is how local clients (Claude Desktop, Claude
         Code, Zed) launch the server as a subprocess.
    """
    platform_port = os.getenv("DATABRICKS_APP_PORT") or os.getenv("PORT")

    if platform_port:
        mcp.run(transport="http", host="0.0.0.0", port=int(platform_port))
    elif settings.mcp_transport == "streamable-http":
        mcp.run(
            transport="streamable-http",
            host=settings.mcp_host,
            port=settings.mcp_port,
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
