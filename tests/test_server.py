"""Smoke and functional tests for the Flood KG MCP server.

Tool-behaviour tests use FastMCP's in-memory Client so they exercise the full
registration and serialisation path without needing a real transport.
"""

from __future__ import annotations

import pytest
from fastmcp import Client, FastMCP

from flood_kg_mcp.app import mcp
from flood_kg_mcp.config import settings
from flood_kg_mcp.utils import (
    get_store,  # noqa: F401 (used in test_store_loads_triples)
)

# ── Server bootstrap ──────────────────────────────────────────────────────────


def test_server_is_importable():
    assert mcp is not None


def test_server_has_name():
    assert mcp.name == "Flood Knowledge Graph MCP Server"


def test_default_transport_is_stdio():
    """Guard against accidentally shipping with a non-stdio default."""
    assert settings.mcp_transport == "stdio"


# ── Submodule registration ────────────────────────────────────────────────────


def test_tools_register_without_error():
    from flood_kg_mcp.tools import register_tools

    register_tools(FastMCP("test"))


def test_prompts_register_without_error():
    from flood_kg_mcp.prompts import register_prompts

    register_prompts(FastMCP("test"))


def test_resources_register_without_error():
    from flood_kg_mcp.resources import register_resources

    register_resources(FastMCP("test"))


def test_routes_register_without_error():
    from flood_kg_mcp.routes import register_routes

    register_routes(FastMCP("test"))


# ── Tool discoverability ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_all_kg_tools_are_discoverable():
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "kg_list_classes" in names
    assert "kg_list_predicates_for_class" in names
    assert "kg_sample_instances" in names
    assert "kg_run_sparql" in names
    assert "kg_get_schema" in names
    assert "kg_get_query_guidelines" in names


@pytest.mark.asyncio
async def test_example_tool_is_gone():
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "example_search_datasets" not in names


# ── KG store ──────────────────────────────────────────────────────────────────


def test_store_loads_triples():
    """Store must be non-empty — catches a missing or empty data file."""
    assert len(get_store()) > 0


# ── Resources ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_schema_resource_is_registered():
    resources = await mcp.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "kg://schema" in uris


@pytest.mark.asyncio
async def test_query_guidelines_resource_is_registered():
    resources = await mcp.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "kg://query-guidelines" in uris


@pytest.mark.asyncio
async def test_query_guidelines_resource_returns_yaml():
    async with Client(mcp) as client:
        result = await client.read_resource("kg://query-guidelines")
    # FastMCP returns a list of content blobs; the first should be non-empty text
    assert result
    text = result[0].text if hasattr(result[0], "text") else str(result[0])
    assert "system_role" in text
    assert "sparql_generation_rules" in text


# ── Prompt ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_flood_kg_analyst_prompt_is_registered():
    prompts = await mcp.list_prompts()
    names = {p.name for p in prompts}
    assert "flood_kg_analyst" in names


@pytest.mark.asyncio
async def test_flood_kg_analyst_prompt_returns_guidelines():
    async with Client(mcp) as client:
        result = await client.get_prompt("flood_kg_analyst", {})
    # result.messages is a list of PromptMessage objects
    assert result.messages
    text = result.messages[0].content.text
    assert "system_role" in text
    assert "sparql_generation_rules" in text


# ── Tool behaviour (via FastMCP in-memory Client) ─────────────────────────────


@pytest.mark.asyncio
async def test_kg_list_classes_returns_uri_count_label():
    async with Client(mcp) as client:
        result = await client.call_tool("kg_list_classes", {})
    rows = result.data
    assert isinstance(rows, list)
    assert len(rows) > 0
    first = rows[0]
    assert "uri" in first
    assert "instance_count" in first
    assert "label" in first
    # URIs must be plain strings, not angle-bracketed
    assert not first["uri"].startswith("<")


@pytest.mark.asyncio
async def test_kg_list_predicates_rejects_bad_uri():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kg_list_predicates_for_class",
            {"class_uri": "not-a-valid-iri"},
        )
    data = result.data
    assert isinstance(data, dict)
    assert "error" in data


@pytest.mark.asyncio
async def test_kg_list_predicates_valid_class():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kg_list_predicates_for_class",
            {"class_uri": "http://floodkg.org/FloodEvent"},
        )
    predicates = result.data
    assert isinstance(predicates, list)
    assert len(predicates) > 0
    assert not predicates[0].startswith("<")


@pytest.mark.asyncio
async def test_kg_sample_instances_returns_results():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kg_sample_instances",
            {"class_uri": "http://floodkg.org/FloodEvent", "limit": 2},
        )
    data = result.data
    assert isinstance(data, list)
    assert len(data) <= 2
    if data:
        assert "subject" in data[0]
        assert "properties" in data[0]
        assert not data[0]["subject"].startswith("<")


@pytest.mark.asyncio
async def test_kg_sample_instances_rejects_bad_uri():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kg_sample_instances",
            {"class_uri": "not-a-uri", "limit": 5},
        )
    data = result.data
    assert isinstance(data, dict)
    assert "error" in data


@pytest.mark.asyncio
async def test_kg_run_sparql_select():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kg_run_sparql",
            {"query": "SELECT ?s WHERE { ?s ?p ?o } LIMIT 3"},
        )
    data = result.data
    assert "results" in data
    assert len(data["results"]) <= 3


@pytest.mark.asyncio
async def test_kg_run_sparql_ask():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kg_run_sparql",
            {"query": "ASK { ?s ?p ?o }"},
        )
    data = result.data
    assert "result" in data
    assert data["result"] is True


@pytest.mark.asyncio
async def test_kg_run_sparql_rejects_construct():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kg_run_sparql",
            {"query": "CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o } LIMIT 1"},
        )
    data = result.data
    assert "error" in data


@pytest.mark.asyncio
async def test_kg_run_sparql_rejects_insert():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kg_run_sparql",
            {"query": "INSERT DATA { <http://x> <http://y> <http://z> }"},
        )
    data = result.data
    assert "error" in data
    assert "hint" in data


@pytest.mark.asyncio
async def test_kg_run_sparql_bad_syntax_returns_error_dict():
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kg_run_sparql",
            {"query": "THIS IS NOT SPARQL"},
        )
    data = result.data
    assert "error" in data
    assert "hint" in data


@pytest.mark.asyncio
async def test_kg_run_sparql_truncation_flag():
    """A query returning more than MAX_ROWS rows must set truncated=True."""
    from flood_kg_mcp.tools.run_sparql import MAX_ROWS

    async with Client(mcp) as client:
        result = await client.call_tool(
            "kg_run_sparql",
            {"query": "SELECT ?s ?p ?o WHERE { ?s ?p ?o }"},
        )
    data = result.data
    assert data.get("truncated") is True
    assert len(data["results"]) == MAX_ROWS


@pytest.mark.asyncio
async def test_kg_run_sparql_injects_missing_prefixes():
    """A query using rdf: without declaring it should still succeed."""
    async with Client(mcp) as client:
        result = await client.call_tool(
            "kg_run_sparql",
            {"query": "SELECT DISTINCT ?class WHERE { ?s rdf:type ?class } LIMIT 5"},
        )
    data = result.data
    assert "results" in data
    assert len(data["results"]) > 0


def test_kg_run_sparql_partial_prefix_injection():
    """A query declaring kg: but not rdf: should get rdf: injected only."""
    from flood_kg_mcp.tools.run_sparql import _inject_missing_prefixes

    query = "PREFIX kg: <http://floodkg.org/>\nSELECT ?s WHERE { ?s rdf:type ?c }"
    injected = _inject_missing_prefixes(query)
    assert "PREFIX rdf:" in injected
    assert injected.count("PREFIX kg:") == 1


@pytest.mark.asyncio
async def test_kg_get_schema_returns_county_designation_properties():
    async with Client(mcp) as client:
        result = await client.call_tool("kg_get_schema", {})
    text = result.data if isinstance(result.data, str) else str(result.data)
    assert "county_designation_properties" in text


@pytest.mark.asyncio
async def test_kg_get_query_guidelines_returns_hallucination_prevention():
    async with Client(mcp) as client:
        result = await client.call_tool("kg_get_query_guidelines", {})
    text = result.data if isinstance(result.data, str) else str(result.data)
    assert "hallucination_prevention" in text
