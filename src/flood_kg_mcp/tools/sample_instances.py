"""Tool: kg_sample_instances — fetch sample instances of an RDF class.

Returns up to `limit` subjects typed as the given class, each with all their
predicate-object pairs.

class_uri is validated via pyoxigraph.NamedNode (rejects malformed IRIs) and
bound through store.query() substitutions — never interpolated into query text.
limit is validated as an integer 1-50 before use.
"""

from __future__ import annotations

from typing import Annotated

import pyoxigraph
from fastmcp import FastMCP

from flood_kg_mcp.utils import get_store

# {{ }} escapes literal braces so .format() only touches {limit}.
_SUBJECTS_QUERY = """\
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?s ?class
WHERE {{ ?s rdf:type ?class . }}
LIMIT {limit}
"""

# All predicate-object pairs for a single subject, bound via substitutions.
_PO_QUERY = """\
SELECT ?p ?o ?s
WHERE { ?s ?p ?o . }
"""


def register(mcp: FastMCP) -> None:
    """Register the kg_sample_instances tool with the MCP server."""

    @mcp.tool(
        name="kg_sample_instances",
        output_schema=None,
        annotations={
            "title": "Sample Instances of a KG Class",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kg_sample_instances(
        class_uri: Annotated[
            str,
            "Full URI of the class to sample, e.g. http://floodkg.org/FloodEvent. "
            "Call kg_list_classes to discover available class URIs.",
        ],
        limit: Annotated[
            int,
            "Number of instances to return (1–50, default 10).",
        ] = 10,
    ) -> dict:
        """Return a sample of instances for a given RDF class.

        Returns {"results": [...]} where each item contains:
          - subject:    the instance URI (or blank-node identifier)
          - properties: list of {predicate, object} pairs for that subject

        Returns an error dict if class_uri is not a valid IRI or limit is
        out of range.

        Read kg://schema for namespace prefixes and query guidance before
        writing SPARQL against this graph.
        """
        if not 1 <= limit <= 50:
            return {
                "error": f"limit must be between 1 and 50, got {limit}.",
                "hint": "Use a limit between 1 and 50.",
            }

        try:
            class_node = pyoxigraph.NamedNode(class_uri)
        except ValueError:
            return {
                "error": f"Invalid class URI: {class_uri!r}",
                "hint": "Call kg_list_classes to get valid class URIs.",
            }

        store = get_store()
        class_var = pyoxigraph.Variable("class")
        subj_var = pyoxigraph.Variable("s")

        # Collect the raw subject terms (NamedNode or BlankNode) directly from
        # the query result — do not reconstruct via NamedNode(uri) so that
        # blank-node subjects survive to the second query.
        subject_terms = [
            solution["s"]
            for solution in store.query(
                _SUBJECTS_QUERY.format(limit=limit),
                substitutions={class_var: class_node},
            )
        ]

        results = []
        for subj_term in subject_terms:
            pairs = [
                {
                    "predicate": row["p"].value,
                    "object": row["o"].value,
                }
                for row in store.query(
                    _PO_QUERY,
                    substitutions={subj_var: subj_term},
                )
            ]
            results.append({"subject": subj_term.value, "properties": pairs})

        return {"results": results}
