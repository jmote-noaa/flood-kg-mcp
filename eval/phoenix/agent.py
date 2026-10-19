"""
FloodKGAgent — LangChain agent connecting to the Flood KG MCP server over stdio.

Usage (smoke test):
    cd eval/phoenix
    uv run python agent.py
"""

from __future__ import annotations

import asyncio
import os
import threading
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = Path(__file__).parent / "prompts"


def _normalise_base_url(raw: str) -> str:
    """Return a base URL that ends with /api/v1, regardless of whether the
    value in .env already includes that suffix or not.

    Examples
    --------
    "https://us-south.ml.cloud.ibm.com"          -> ".../api/v1"
    "https://us-south.ml.cloud.ibm.com/api/v1"   -> ".../api/v1"  (unchanged)
    "https://us-south.ml.cloud.ibm.com/api/v1/"  -> ".../api/v1"  (stripped)
    """
    url = raw.rstrip("/")
    if not url.endswith("/api/v1"):
        url = url + "/api/v1"
    return url


# Default model — read from .env. Must match an exact USAi model identifier.
# To list available ids, populate .env then run:
#   uv run python -c "
#     import httpx, os; from dotenv import load_dotenv; load_dotenv()
#     r = httpx.get(os.getenv('USAI_BASE_URL').rstrip('/')+'/api/v1/models',
#           headers={'Authorization': 'Bearer '+os.getenv('USAI_API_KEY')})
#     [print(m['id']) for m in r.json()['data']]"
_DEFAULT_MODEL = os.getenv("AGENT_MODEL", "")
BASE_URL = _normalise_base_url(os.getenv("USAI_BASE_URL", ""))
API_KEY = os.getenv("USAI_API_KEY", "")


class FloodKGAgent:
    """LangChain ReAct agent wired to the Flood KG MCP server over stdio.

    Args:
        system_prompt_version: "v1" (tool-call baseline) or "v2" (schema inlined).
        model: USAi model identifier. Defaults to AGENT_MODEL from .env.
               Pass explicitly to run the same dataset against multiple models.
    """

    def __init__(
        self,
        system_prompt_version: str = "v1",
        model: str | None = None,
    ):
        self.system_prompt_version = system_prompt_version
        self.model = model or _DEFAULT_MODEL
        if not self.model:
            raise ValueError(
                "No model specified. Set AGENT_MODEL in .env or pass model= explicitly."
            )
        self._agent = None
        self._client = None
        self._tracer_provider = None

    # ── Prompt loading ────────────────────────────────────────────────────────

    def _load_system_prompt(self) -> str:
        """Load the versioned system prompt, filling placeholders for v2."""
        path = PROMPTS_DIR / f"system_prompt_{self.system_prompt_version}.txt"
        template = path.read_text(encoding="utf-8")

        if self.system_prompt_version == "v2":
            schema = (REPO_ROOT / "data" / "schema_prototype2.yml").read_text(
                encoding="utf-8"
            )
            guidelines = (REPO_ROOT / "data" / "prompt_guidelines2.yml").read_text(
                encoding="utf-8"
            )
            return template.format(kg_schema=schema, kg_guidelines=guidelines)

        return template

    # ── Phoenix instrumentation ───────────────────────────────────────────────

    def initialize(
        self,
        project_name: str = "flood-kg-eval",
        phoenix_endpoint: str = "http://localhost:6006",
    ) -> None:
        """Instrument LangChain with Phoenix tracing. Call once before running."""
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from phoenix.otel import register

        self._tracer_provider = register(
            project_name=project_name,
            endpoint=f"{phoenix_endpoint}/v1/traces",
        )
        LangChainInstrumentor().instrument(tracer_provider=self._tracer_provider)

    # ── Agent lifecycle ───────────────────────────────────────────────────────

    async def _build(self) -> None:
        """Lazily create the MCP client and LangChain agent."""
        if self._agent is not None:
            return

        from langchain_mcp_adapters.client import MultiServerMCPClient
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent

        self._client = MultiServerMCPClient({
            "flood_kg_server": {
                "transport": "stdio",
                "command": "uv",
                "args": ["run", "python", "src/flood_kg_mcp/app.py"],
                "cwd": str(REPO_ROOT),
            }
        })
        tools = await self._client.get_tools()

        llm = ChatOpenAI(
            model=self.model,
            base_url=BASE_URL,
            api_key=API_KEY,
            temperature=0,
        )
        self._agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=self._load_system_prompt(),
        )

    async def run(self, query: str) -> str:
        """Run a single query and return the text response."""
        await self._build()
        result = await self._agent.ainvoke({"messages": [("user", query)]})
        for msg in reversed(result["messages"]):
            content = getattr(msg, "content", None)
            if content:
                return content if isinstance(content, str) else str(content)
        return str(result)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.__aexit__(None, None, None)

    # ── Sync task factory for Phoenix experiments ─────────────────────────────

    def create_experiment_task(self):
        """Return a sync task(example) callable for phoenix run_experiment.

        Uses a single persistent event loop on a background thread shared across
        all questions in a dataset run.  The MCP client and its underlying async
        transport are created once (via _build) and reused for every question,
        avoiding "bound to a different event loop" errors that occur when
        asyncio.run() creates a fresh loop per call.
        """
        loop = asyncio.new_event_loop()

        def _runner():
            asyncio.set_event_loop(loop)
            loop.run_forever()

        thread = threading.Thread(
            target=_runner, daemon=True, name="flood-kg-eval-loop"
        )
        thread.start()

        # Build agent eagerly so the first question doesn't pay startup cost.
        asyncio.run_coroutine_threadsafe(self._build(), loop).result(timeout=60)

        agent = self

        def task(example) -> str:
            return asyncio.run_coroutine_threadsafe(
                agent.run(example.input["query"]), loop
            ).result(timeout=120)

        return task


# ── Smoke test ────────────────────────────────────────────────────────────────

async def _smoke_test() -> None:
    agent = FloodKGAgent(system_prompt_version="v1")
    print(f"Model : {agent.model}")
    print(f"URL   : {BASE_URL}")
    print("Query : 'How many flood events are in the graph?'")
    answer = await agent.run("How many flood events are in the graph?")
    print(f"Answer: {answer}")
    await agent.close()


def main() -> None:
    asyncio.run(_smoke_test())


if __name__ == "__main__":
    main()
