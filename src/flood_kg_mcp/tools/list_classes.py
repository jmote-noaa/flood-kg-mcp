"""Tool: kg_list_classes — list every RDF class in the knowledge graph.

Returns each class URI with its instance count (COUNT DISTINCT to avoid
overcounting when a subject has multiple rdf:type triples for the same class)
and its rdfs:label if one exists, sorted by instance count descending.
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from flood_kg_mcp.utils import get_store

_log = logging.getLogger(__name__)

_QUERY = """\
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?class (COUNT(DISTINCT ?s) AS ?count) (SAMPLE(?lbl) AS ?label)
WHERE {
  ?s rdf:type ?class .
  OPTIONAL { ?class rdfs:label ?lbl }
}
GROUP BY ?class
ORDER BY DESC(?count)
"""


def register(mcp: FastMCP) -> None:
    """Register the kg_list_classes tool with the MCP server."""

    @mcp.tool(
        name="kg_list_classes",
        output_schema=None,
        annotations={
            "title": "List KG Classes",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kg_list_classes() -> dict:
        """List every RDF class in the Texas Flood Knowledge Graph.

        Returns {"results": [...]} where each item has:
          - uri:            the full class URI (plain string, no angle brackets)
          - label:          rdfs:label value if present, otherwise null
          - instance_count: number of distinct subjects typed as this class

        Call kg_get_schema for namespace prefixes and query guidance before
        writing SPARQL against this graph.
        """
        _log.info("tool=kg_list_classes")
        store = get_store()
        rows = []
        for solution in store.query(_QUERY):
            label_term = solution["label"]
            rows.append(
                {
                    "uri": solution["class"].value,
                    "label": label_term.value if label_term is not None else None,
                    "instance_count": int(solution["count"].value),
                }
            )
        return {"results": rows}
