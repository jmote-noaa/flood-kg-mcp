# Texas Flood Knowledge Graph MCP Server

An MCP server that gives AI agents direct, read-only SPARQL access to the **Texas Flood Systems Knowledge Graph**, an integrated graph linking flood hazards to community vulnerability across Texas counties.

Built for GSA's 2026 MCP Server and AI Agent Hackathon (data track, IBM watsonx Orchestrate + Bob), from the [GSA-TTS hackathon template](https://github.com/GSA-TTS/mcp-hackathon-template).

**This server does not call an external API.** The graph is bundled with the server, loaded into an in-memory [Oxigraph](https://github.com/oxigraph/oxigraph) store at startup, and queried with SPARQL.

---

## What it does

Most MCP servers wrap a REST API with a fixed set of endpoints. This one exposes a knowledge graph instead: an agent can discover the graph's structure, read documented schema and analytical guidance, and write its own SPARQL queries across four datasets joined through shared county entities.

| Dataset | Content in the graph |
|---|---|
| NOAA Storm Events | 1,540 flood, flash flood, and coastal flood events |
| FEMA Disaster Declarations | Declarations and 177 per-county designations with program flags (PA, IH, HM, IA) |
| Census ACS | County demographic, economic, housing, communications, education, and transportation indicators |
| NWS Watches and Warnings | 1,350 county-based flash flood warnings, 2023–2025 (via Iowa Environmental Mesonet) |

The graph is grounded in a flood ontology developed through a participatory expert workshop co-hosted with the Natural Hazards Center.

### How the data is served: Oxigraph as an in-memory triple store

The MCP server queries an embedded [Oxigraph](https://github.com/oxigraph/oxigraph) triple store, used through its Python binding, [pyoxigraph](https://pyoxigraph.readthedocs.io/). There is no separate database server:

1. **At startup**, the server loads `data/texas_flood2.ttl` (108,137 triples, roughly 10 MB of Turtle) into an in-memory Oxigraph store. Loading takes about a second, and the server fails fast if the file is missing or malformed.
2. **On each tool call**, the SPARQL query runs directly against that store inside the same process. No network hop and no external service are involved.
3. **The store is read-only in practice.** The server only ever runs SELECT and ASK queries against it, and it is rebuilt from the Turtle file on every start, so nothing an agent does can change the data.

This keeps deployment to a single container: the graph ships inside the image, and Oxigraph supports full SPARQL 1.1 querying without a database to install or operate. The trade-offs are that the whole graph lives in memory (well under 1 GB here), that each cold start reloads it, and that updating the data means rebuilding the image. A larger or frequently updated graph would move to a hosted triple store, such as Amazon Neptune or GraphDB, with the MCP tools unchanged apart from where queries are sent.

Example questions the agent answers:
- *Which counties are most vulnerable to flooding?* (separate rankings for each vulnerability indicator)
- *Which FEMA-designated counties have the highest poverty rates?*
- *How many counties received both NWS flood warnings and FEMA disaster declarations?*

---

## Tools, resources, and prompt

| Name | Type | Purpose |
|---|---|---|
| `kg_get_schema` | Tool | Returns the schema: classes, properties, indicator formulas, analytical constructs, common graph paths |
| `kg_get_query_guidelines` | Tool | Returns analyst guidelines: SPARQL rules, county reporting, hallucination prevention |
| `kg_list_classes` | Tool | Lists classes with instance counts and labels |
| `kg_list_predicates_for_class` | Tool | Lists the properties used by a class |
| `kg_sample_instances` | Tool | Returns example instances with all their properties (up to 50) |
| `kg_run_sparql` | Tool | Runs read-only SELECT or ASK queries; 200-row cap with a truncation flag |
| `kg://schema`, `kg://query-guidelines` | Resources | Same content as the two `get` tools, for clients that read MCP resources |
| `flood_kg_analyst` | Prompt | The guidelines packaged as an analyst system prompt |

The schema and guidelines are also exposed as tools because some clients, including watsonx Orchestrate and LangChain's MCP adapter, load only tools.

### Safety

- **Read-only.** Update queries are rejected by the store; CONSTRUCT and DESCRIBE are rejected by result type.
- **No SPARQL injection.** Class URIs supplied by agents are validated as IRIs and bound as query parameters, never inserted into query text.
- **Bounded results.** SELECT results are capped at 200 rows, and errors return a message with a hint rather than a stack trace.
- **Logging.** Each tool call is logged, including the SPARQL text and row count, so every answer can be traced to the query that produced it.

---

## Architecture

```
User → watsonx Orchestrate agent → MCP (streamable HTTP) → IBM Code Engine
                                                            └─ FastMCP server
                                                               └─ Oxigraph in-memory triple store
                                                                  (pyoxigraph, loaded from
                                                                   data/texas_flood2.ttl)
```

| Path | Contents |
|---|---|
| `src/flood_kg_mcp/` | Server: tools, resources, prompt, store loading |
| `data/` | The graph (`texas_flood2.ttl`), schema, and analyst guidelines |
| `deploy/ibm/agent/flood_agent.yaml` | The Orchestrate agent definition (instructions, guidelines, tools) |
| `eval/phoenix/` | Evaluation harness and gold dataset |
| `tests/` | 48 tests, run through FastMCP's in-memory client |

---

## Running locally

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python main.py          # stdio mode, for local MCP clients
```

```bash
uv sync --group dev
uv run pytest tests/ -v
uv run ruff check . && uv run ruff format --check .
```

## Deploying

The server runs as a container on IBM Code Engine (`Dockerfile`; dependencies pinned to `uv.lock`) and serves MCP at `/mcp`. To register it with watsonx Orchestrate and load the agent:

```bash
orchestrate toolkits add --kind mcp --name <toolkit-name> \
  --description "Texas Flood Knowledge Graph" \
  --url "https://<your-app-url>/mcp" --transport "streamable_http" --tools "*"
orchestrate agents import -f deploy/ibm/agent/flood_agent.yaml
```

The agent file refers to tools by toolkit name, so update its `tools:` entries if you use a different name.

---

## Evaluation

A 10-question gold dataset (`eval/phoenix/datasets/flood-eval-0/evaluation.xml`) covers counts, cross-dataset joins, rates, a multi-indicator construct, a derived property, a refusal case, and an out-of-scope case. Every gold answer was produced by running SPARQL directly against the graph; the queries are in `eval/phoenix/scratch/`.

**watsonx Orchestrate agent: 10/10.** Each question was asked in a fresh chat and checked against the gold answer and the server logs.

Three findings from that testing:
1. **The model fabricated results despite correct queries.** For two questions, the agent wrote the right SPARQL and received the right rows, then presented invented ones. A guideline requiring it to report only rows returned by `kg_run_sparql` fixed this.
2. **The model built a composite score the schema forbids.** A guideline and instruction to decline composite indexes and offer individual indicators fixed this.
3. **Earlier answers leak into later ones.** In a continuing chat, the agent reused a previous result instead of applying a new filter. Evaluation questions should each run in a fresh chat.

Building the gold answers also surfaced and fixed several schema errors (program flags documented on the wrong class, an undercounted elderly population, NWS coverage overstated) that would have misled any agent.

An automated harness using [Arize Phoenix](https://docs.arize.com/phoenix) with LLM judges is in `eval/phoenix/`. It compares a minimal prompt with one that includes the schema up front, across multiple models. See `eval/phoenix/README.md`.

---

## Known limitations

- NWS data contains flash flood warnings (FF) only; flood warnings (FA) were lost in the graph build.
- One FEMA declaration title has a trailing space (`"HURRICANE BERYL "`), so exact title matches fail.
- The broadband access rate divides by households with internet access, which leaves little variation between counties.
- Indicators for very small counties (such as Loving and Kenedy) are based on few residents and can be extreme.
- SPARQL queries have no execution timeout.
- The deployed endpoint has no authentication, matching the hackathon's public-data setup.

## License

MIT. See [LICENSE](LICENSE) and [SECURITY.md](SECURITY.md).
running SPARQL directly against the graph; the queries are in `eval/phoenix/scratch/`.

**watsonx Orchestrate agent: 10/10.** Each question was asked in a fresh chat and checked against the gold answer and the server logs.

Three findings from that testing:
1. **The model fabricated results despite correct queries.** For two questions, the agent wrote the right SPARQL and received the right rows, then presented invented ones. A guideline requiring it to report only rows returned by `kg_run_sparql` fixed this.
2. **The model built a composite score the schema forbids.** A guideline and instruction to decline composite indexes and offer individual indicators fixed this.
3. **Earlier answers leak into later ones.** In a continuing chat, the agent reused a previous result instead of applying a new filter. Evaluation questions should each run in a fresh chat.

Building the gold answers also surfaced and fixed several schema errors (program flags documented on the wrong class, an undercounted elderly population, NWS coverage overstated) that would have misled any agent.

An automated harness using [Arize Phoenix](https://docs.arize.com/phoenix) with LLM judges is in `eval/phoenix/`. It compares a minimal prompt with one that includes the schema up front, across multiple models. See `eval/phoenix/README.md`.

---

## Known limitations

- NWS data contains flash flood warnings (FF) only; flood warnings (FA) were lost in the graph build.
- One FEMA declaration title has a trailing space (`"HURRICANE BERYL "`), so exact title matches fail.
- The broadband access rate divides by households with internet access, which leaves little variation between counties.
- Indicators for very small counties (such as Loving and Kenedy) are based on few residents and can be extreme.
- SPARQL queries have no execution timeout.
- The deployed endpoint has no authentication, matching the hackathon's public-data setup.

## License

MIT. See [LICENSE](LICENSE) and [SECURITY.md](SECURITY.md).


[MIT](LICENSE). See [SECURITY.md](SECURITY.md) for the vulnerability disclosure policy.
