# Texas Flood Knowledge Graph MCP Server

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that exposes the **Texas Flood Systems Knowledge Graph** to LLM agents. The graph integrates four datasets through shared county entities:

| Dataset | Description |
|---|---|
| NOAA Storm Events | Flood, flash-flood, and coastal-flood events with damage and casualty data |
| FEMA Disaster Declarations | Federal declarations with per-county program designations (PA, IH, HM) |
| ACS (American Community Survey) | Demographic, economic, housing, and communications indicators per county |
| NWS Flash Flood Warnings | County-level flash flood warnings, 2023–2025 (Iowa Environmental Mesonet) |

Built with [FastMCP](https://github.com/jlowin/fastmcp), [pyoxigraph](https://github.com/oxigraph/oxigraph), and [uv](https://docs.astral.sh/uv/).

---

## What the server exposes

### Tools

| Tool | Description |
|---|---|
| `kg_get_schema` | Full schema YAML — namespaces, classes, indicator formulas, analytical constructs, and SPARQL graph paths |
| `kg_get_query_guidelines` | Full analyst guidelines YAML — reasoning rules, SPARQL conventions, cross-dataset patterns, hallucination prevention |
| `kg_list_classes` | List every RDF class with instance counts |
| `kg_list_predicates_for_class` | List predicates for a given class URI |
| `kg_sample_instances` | Fetch sample instances with all properties |
| `kg_run_sparql` | Execute a read-only SELECT or ASK query (200-row cap, default prefixes injected) |

### Resources

| URI | Description |
|---|---|
| `kg://schema` | Schema YAML (same content as `kg_get_schema`) |
| `kg://query-guidelines` | Guidelines YAML (same content as `kg_get_query_guidelines`) |

`kg_get_schema` and `kg_get_query_guidelines` exist as tools so LangChain-based agents (which load tools but not MCP resources) can access the schema without a resource read.

### Prompt

`flood_kg_analyst` — analyst system instructions covering the full reasoning and SPARQL workflow. Load at the start of a query session.

---

## Getting started

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — `pip install uv`

### Install and run

```powershell
# copy env template and fill in any overrides (defaults work for local dev)
Copy-Item .env.example .env
uv sync
uv run python main.py
```

The server starts in **stdio** mode — it communicates over stdin/stdout, which is how local clients (Claude Desktop, Claude Code) launch it as a subprocess.

### Connect a client (Claude Code)

Add to `.mcp.json` (or your user MCP config), using the **absolute path** to this repo:

```json
{
  "mcpServers": {
    "flood-kg": {
      "command": "uv",
      "args": ["run", "flood-kg-mcp"],
      "cwd": "C:\\path\\to\\flood-kg-mcp"
    }
  }
}
```

### Verify

```powershell
uv sync --group dev
uv run pytest tests/ -v        # 48 tests
uv run ruff check .            # lint
uv run ruff format --check .   # format
```

---

## Repo structure

```
flood-kg-mcp/
├── main.py                         # Local entry point
├── pyproject.toml                  # Dependencies (uv)
├── .env.example                    # Env var template
├── data/
│   ├── texas_flood2.ttl            # Knowledge graph (Turtle)
│   ├── schema_prototype2.yml       # Schema + indicator formulas (kg://schema)
│   └── prompt_guidelines2.yml      # Analyst guidelines (kg://query-guidelines)
├── src/flood_kg_mcp/
│   ├── app.py                      # Server entry point + transport selection
│   ├── config.py                   # Settings from env / .env
│   ├── tools/
│   │   ├── get_schema.py           # kg_get_schema
│   │   ├── get_query_guidelines.py # kg_get_query_guidelines
│   │   ├── list_classes.py         # kg_list_classes
│   │   ├── list_predicates_for_class.py
│   │   ├── sample_instances.py     # kg_sample_instances
│   │   └── run_sparql.py           # kg_run_sparql
│   ├── prompts/
│   │   └── flood_kg_analyst.py     # flood_kg_analyst prompt
│   └── resources/
│       ├── schema.py               # kg://schema
│       └── query_guidelines.py     # kg://query-guidelines
├── tests/                          # Pytest suite (server, tools, security)
├── eval/
│   ├── phoenix/                    # LangChain + Phoenix eval harness
│   │   ├── agent.py                # FloodKGAgent (stdio, multi-model)
│   │   ├── create_dataset.py       # CLI: upload CSV to Phoenix
│   │   ├── run_experiment.py       # CLI: run agent + judges
│   │   ├── judges/                 # LLM-as-judge evaluators
│   │   ├── prompts/                # system_prompt_v1.txt / v2.txt
│   │   └── datasets/flood-eval-0/ # 10-question gold set + CSV
│   └── databricks/                 # MLflow eval for deployed Databricks app
└── deploy/
    ├── ibm/                        # watsonx Orchestrate (3 kits)
    └── databricks/                 # Databricks Apps kit
```

---

## Analytical constructs

The schema defines four analytical constructs that agents must follow:

| Construct | Primary indicators | Approach |
|---|---|---|
| **vulnerability** | poverty_rate, elderly_share, mobile_home_share, vehicle_access_deficit | Separate ranked query per indicator — never a composite index |
| **resilience** | broadband_access_rate, internet_access_rate, bachelors_rate, owner_share | Rank counties per indicator; lower vehicle_access_deficit = more resilient |
| **exposure** | nws_warning_frequency + vulnerability indicators | Cross-dataset join through County; always combine a hazard measure with ACS |
| **recovery_capacity** | median_hh_income, owner_share, broadband_access_rate | Not pre-computed; acknowledge limitation when asked directly |

Composite indices not defined in the schema must be declined. See `kg://schema` for full indicator formulas and `kg://query-guidelines` for the hallucination-prevention rules.

---

## Evaluation

A 10-question gold evaluation set with verified SPARQL ground truth lives in [`eval/phoenix/datasets/flood-eval-0/`](eval/phoenix/datasets/flood-eval-0/). The Phoenix harness supports:

- Multiple agent models compared sequentially in a single run
- Two prompt versions: v1 (tool-call baseline) and v2 (schema inlined at runtime)
- Two LLM-as-judge evaluators: correctness (numeric tolerance, ranked-list 80% rule) and scope (appropriate/inappropriate handling)

See [`eval/phoenix/README.md`](eval/phoenix/README.md) for setup and usage.

---

## Deploying

`app.py` auto-selects transport based on the environment:

- Platform-injected port (`DATABRICKS_APP_PORT` or `PORT`) → HTTP
- `MCP_TRANSPORT=streamable-http` → HTTP on `MCP_HOST:MCP_PORT`
- Otherwise → stdio

See [`deploy/README.md`](deploy/README.md) for deployment kits:

- **IBM watsonx Orchestrate** — [`deploy/ibm/`](deploy/ibm/) (local stdio toolkit, Code Engine build-from-Git, or prebuilt image)
- **Databricks Apps** — [`deploy/databricks/`](deploy/databricks/)

---

## License

[MIT](LICENSE). See [SECURITY.md](SECURITY.md) for the vulnerability disclosure policy.
