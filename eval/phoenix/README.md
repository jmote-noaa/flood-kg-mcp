# Texas Flood KG — Phoenix Evaluation Harness

Evaluates how well an LLM agent can answer flood-knowledge questions using only
the MCP server's tools. Scores each answer with two LLM-as-judge evaluators and
logs traces to [Arize Phoenix](https://docs.arize.com/phoenix).

## Layout

```
eval/phoenix/
├── agent.py               # FloodKGAgent — launches server over stdio
├── create_dataset.py      # CLI: upload CSV dataset to Phoenix
├── run_experiment.py      # CLI: run agent + judges against a dataset
├── datasets.yaml          # Dataset registry
├── judges/
│   ├── correctness_judge.py   # match_expected_response
│   └── relevance_judge.py     # check_answer_scope
├── prompts/
│   ├── system_prompt_v1.txt   # Baseline: role + "call kg_get_schema/guidelines"
│   └── system_prompt_v2.txt   # Template: role + both YAML files inlined at runtime
└── datasets/
    └── flood-eval-0/
        ├── evaluation.xml              # Gold question set (source)
        └── examples/flood-eval-0.csv  # Generated dataset (query, responses)
```

## Setup

```powershell
# 1. Install eval deps (already declared in pyproject.toml [dependency-groups] dev):
uv sync --group dev

# 2. Add these keys to your existing .env:
#   USAI_BASE_URL  — your USAi gateway base URL (without /api/v1 suffix)
#   USAI_API_KEY   — your API key
#   AGENT_MODEL    — model id for the agent under test
#   JUDGE_MODEL    — model id for the LLM judges (use a strong model)

# 3. Check available USAi model ids — run from the repo root so agent.py is on
#    the path (run as a single line in PowerShell):
uv run python -c "import httpx, os, sys; sys.path.insert(0,'eval/phoenix'); from dotenv import load_dotenv; load_dotenv(); from agent import _normalise_base_url, API_KEY; url = _normalise_base_url(os.getenv('USAI_BASE_URL','')); r = httpx.get(url + '/models', headers={'Authorization': 'Bearer ' + API_KEY}); r.raise_for_status(); [print(m['id']) for m in r.json()['data']]"
```

## Run

All commands from `eval/phoenix/`. Start Phoenix in its own terminal and leave it
running while you run the other commands.

```powershell
# Terminal 1 — start Phoenix (UI at http://localhost:6006, leave this running):
uv run phoenix serve

# Terminal 2 — validate the CSV (no upload):
uv run create_dataset.py --dataset-name flood-eval-0 --dry-run

# Upload dataset to Phoenix (one-time):
uv run create_dataset.py --dataset-name flood-eval-0

# Run eval — single model from .env:
uv run run_experiment.py --dataset-name flood-eval-0

# Run eval — compare two models (PowerShell uses backtick ` for line continuation):
uv run run_experiment.py --dataset-name flood-eval-0 `
    --agent-model <model-id-1> `
    --agent-model <model-id-2>

# Run with v2 prompt (schema inlined):
uv run run_experiment.py --dataset-name flood-eval-0 --system-prompt-version v2
```

> **Note:** The multi-model example above uses PowerShell backtick (`` ` ``) for
> line continuation. On bash/zsh use `\` instead.

## Prompt versions

| Version | What it does |
|---|---|
| `v1` | Baseline: role description + instruction to call `kg_get_schema` and `kg_get_query_guidelines`. Agent must make tool calls to learn the schema. |
| `v2` | Template: same as v1, but both YAML files are inlined at runtime from `data/`. Agent has the schema in context without a tool call. |

Use v1 vs v2 to measure how much the agent benefits from having context upfront
vs. how well it discovers the schema through tool calls.

## Judges

| Judge | Evaluates |
|---|---|
| `match_expected_response` | Whether the answer contains the key facts from the gold answer. Allows wording/formatting differences. |
| `check_answer_scope` | Whether the agent answered in-scope questions and correctly declined out-of-scope ones. |

Both judges use `JUDGE_MODEL` from `.env`. Keep it separate from `AGENT_MODEL`
to avoid self-preference bias.

## Dataset: flood-eval-0

10 questions covering the full range of server capabilities:

| # | Type | Tests |
|---|---|---|
| Q1 | Count | `kg:FloodEvent` class traversal |
| Q2 | Program flag | `paProgramDeclared` on `CountyDesignation` (not `FEMADisasterDeclaration`) |
| Q3 | Ratio + sort | `broadband_access_rate` formula, ASC ordering |
| Q4 | Filter | `incidentType="Hurricane"` on `FEMADisasterDeclaration` |
| Q5 | Cross-dataset + ratio | `fema_exposure` path + `poverty_rate` formula |
| Q6 | Cross-dataset count | NWS ∩ FEMA join through `County` |
| Q7 | Multi-indicator | Vulnerability construct: 4 separate rankings, no composite |
| Q8 | Aggregate | `AVG(warningDurationHours)` on `NWSHazardProduct` |
| Q9 | Refusal | Composite resilience score — not a supported construct |
| Q10 | Out-of-scope | NFIP claims — not in the graph |
