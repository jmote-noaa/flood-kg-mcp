"""Resource: kg://schema — schema and query guidance for the Texas Flood KG.

Agents should read this resource before writing any SPARQL query against the
graph. It is served as YAML with mime_type="application/yaml".
"""

from __future__ import annotations

from fastmcp import FastMCP

from flood_kg_mcp.config import settings


def register(mcp: FastMCP) -> None:
    """Register the kg://schema resource with the MCP server."""

    @mcp.resource("kg://schema", mime_type="application/yaml")
    def kg_schema() -> str:
        """Schema and query guidance for the Texas Flood Knowledge Graph.

        Read this resource before writing any SPARQL query. It covers:

        - Namespaces and prefixes (kg:, flood:, rdf:, rdfs:, xsd:)
        - Dataset classes: County, FloodEvent, FEMADisasterDeclaration,
          CountyDesignation, NWSHazardProduct
        - Primary relationships: occursIn, forCounty, forDeclaration,
          coversCounty
        - Per-dataset property lists: Storm Events, FEMA, ACS (demographics,
          economics, housing, communications, education, transportation),
          and NWS hazard products
        - Analytical concepts with indicator formulas, numerators,
          denominators, and interpretation notes covering economic
          vulnerability, demographic vulnerability, housing vulnerability,
          transportation vulnerability, communications resilience,
          and hazard exposure
        - Analytical constructs (vulnerability, resilience, exposure,
          recovery_capacity) with definitions, primary/secondary indicators,
          and SPARQL approach guidance — including explicit rules about
          what NOT to infer
        - Common graph paths (flood_exposure, fema_exposure, nws_exposure,
          full_exposure) with ready-to-use SPARQL triple patterns for
          cross-dataset county-level queries
        - Important modelling notes: county URI pattern, dataset-class vs
          ontology-class distinction, NWS county-only scope, and guidance
          on using warningDurationHours instead of computing it from
          dateTime arithmetic
        """
        with open(settings.kg_schema_path, encoding="utf-8") as fh:
            return fh.read()
