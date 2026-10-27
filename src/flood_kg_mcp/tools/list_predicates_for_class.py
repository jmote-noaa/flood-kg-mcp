"""Tool: kg_list_predicates_for_class — list predicates used by a given class.

Returns all distinct predicate URIs that appear on subjects typed as the
requested class, sorted alphabetically.

The class_uri is validated by constructing a pyoxigraph.NamedNode, which
rejects any string that is not a well-formed IRI. The validated node is
passed via store.query() substitutions, never interpolated into query text.
"""

from __future__ import annotations

from typing import Annotated

import pyoxigraph
from fastmcp import FastMCP

from flood_kg_mcp.utils import get_store

# ?class must appear in SELECT for pyoxigraph substitutions to accept the binding.
# Its value is constant (the bound node) and is not included in the return value.
_QUERY = """\
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?predicate ?class
WHERE { ?s rdf:type ?class ; ?predicate ?o . }
ORDER BY ?predicate
"""


def register(mcp: FastMCP) -> None:
    """Register the kg_list_predicates_for_class tool with the MCP server."""

    @mcp.tool(
        name="kg_list_predicates_for_class",
        output_schema=None,
        annotations={
            "title": "List Predicates for a KG Class",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kg_list_predicates_for_class(
        class_uri: Annotated[
            str,
            "Full URI of the class whose predicates to list, e.g. "
            "http://floodkg.org/FloodEvent. Call kg_list_classes first to "
            "discover available class URIs.",
        ],
    ) -> dict:
        """List all distinct predicates used by instances of a given RDF class.

        Returns {"results": [...]} with sorted predicate URIs (plain strings,
        no angle brackets). Returns an error dict if class_uri is not a valid IRI.

        Read kg://schema for namespace prefixes and query guidance before
        writing SPARQL against this graph.
        """
        try:
            class_node = pyoxigraph.NamedNode(class_uri)
        except ValueError:
            return {
                "error": f"Invalid class URI: {class_uri!r}",
                "hint": "Call kg_list_classes to get valid class URIs.",
            }

        store = get_store()
        return {
            "results": [
                solution["predicate"].value
                for solution in store.query(
                    _QUERY,
                    substitutions={pyoxigraph.Variable("class"): class_node},
                )
            ]
        }
