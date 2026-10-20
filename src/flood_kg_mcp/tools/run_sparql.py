"""Tool: kg_run_sparql — execute a read-only SPARQL query against the KG.

Only SELECT and ASK queries are accepted. This is enforced by checking the
type of pyoxigraph's query result:
  - QuerySolutions  -> SELECT  (accepted)
  - QueryBoolean    -> ASK     (accepted)
  - QueryTriples    -> CONSTRUCT / DESCRIBE (rejected)
Updates (INSERT, DELETE, DROP, ...) raise a SyntaxError from pyoxigraph before
a result type can be checked, and are surfaced as an error dict.

SELECT results are capped at 200 rows; "truncated": true is included when the
cap is reached so agents know more rows exist.

Default prefixes (kg:, flood:, rdf:, rdfs:, xsd:) are prepended individually
for each prefix the query does not already declare, so a query that uses rdf:
without declaring it still works even if it declares kg:.
"""

from __future__ import annotations

from typing import Annotated

import pyoxigraph
from fastmcp import FastMCP

from flood_kg_mcp.utils import get_store

MAX_ROWS = 200

_DEFAULT_PREFIXES: list[tuple[str, str]] = [
    ("kg", "http://floodkg.org/"),
    ("flood", "http://example.org/flood-ontology#"),
    ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
]


def _inject_missing_prefixes(query: str) -> str:
    """Prepend each default PREFIX the query doesn't already declare."""
    upper = query.upper()
    lines = []
    for prefix, uri in _DEFAULT_PREFIXES:
        if f"PREFIX {prefix.upper()}:" not in upper:
            lines.append(f"PREFIX {prefix}: <{uri}>")
    if lines:
        return "\n".join(lines) + "\n" + query
    return query


def _term_value(term: object) -> str | None:
    """Extract a plain Python value from a pyoxigraph query result term."""
    if term is None:
        return None
    if hasattr(term, "value"):
        return term.value
    return str(term)


def register(mcp: FastMCP) -> None:
    """Register the kg_run_sparql tool with the MCP server."""

    @mcp.tool(
        name="kg_run_sparql",
        annotations={
            "title": "Run SPARQL Query on KG",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def kg_run_sparql(
        query: Annotated[
            str,
            "A SPARQL SELECT or ASK query. CONSTRUCT and DESCRIBE are not supported. "
            "Default prefixes (kg:, flood:, rdf:, rdfs:, xsd:) are added automatically "
            "for any prefix not already declared in the query.",
        ],
    ) -> dict:
        """Execute a read-only SPARQL SELECT or ASK query against the Texas Flood KG.

        SELECT results are returned as a list of row objects under the key
        "results", each mapping variable names to their values (plain strings
        for URIs and literals, null for unbound). When the 200-row cap is
        reached the response also contains "truncated": true.

        ASK results are returned as {"result": true/false}.

        CONSTRUCT and DESCRIBE are rejected. Updates (INSERT, DELETE, etc.)
        are rejected by pyoxigraph before execution.

        Read kg://schema first -- it contains namespace prefixes, class names,
        and example queries for this graph.
        """
        _HINT = (
            "Check your SPARQL syntax. Read kg://schema for the graph "
            "structure, available classes, and example queries."
        )

        full_query = _inject_missing_prefixes(query)

        try:
            result = get_store().query(full_query)

            if isinstance(result, pyoxigraph.QueryBoolean):
                return {"result": bool(result)}

            if isinstance(result, pyoxigraph.QuerySolutions):
                variables = [v.value for v in result.variables]
                rows: list[dict] = []
                truncated = False
                # Iteration is inside the try block: pyoxigraph evaluates
                # lazily, so execution errors can surface during row iteration.
                for solution in result:
                    if len(rows) >= MAX_ROWS:
                        truncated = True
                        break
                    rows.append({v: _term_value(solution[v]) for v in variables})
                response: dict = {"results": rows}
                if truncated:
                    response["truncated"] = True
                return response

            # QueryTriples -- CONSTRUCT or DESCRIBE
            return {
                "error": "CONSTRUCT and DESCRIBE queries are not supported.",
                "hint": "Use SELECT or ASK. Read kg://schema for example queries.",
            }

        except Exception as exc:
            return {"error": str(exc), "hint": _HINT}
