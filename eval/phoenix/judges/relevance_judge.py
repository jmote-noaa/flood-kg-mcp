"""
relevance_judge — LLM-as-judge: is the agent's answer within scope?

Returns "within_scope" or "out_of_scope".
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from phoenix.evals import ClassificationTemplate, LLMClassifier, OpenAIModel

load_dotenv()

_JUDGE_MODEL = os.getenv("JUDGE_MODEL", os.getenv("AGENT_MODEL", ""))
_BASE_URL = os.getenv("USAI_BASE_URL", "").rstrip("/")
if not _BASE_URL.endswith("/api/v1"):
    _BASE_URL = _BASE_URL + "/api/v1"
_API_KEY = os.getenv("USAI_API_KEY", "")

_TEMPLATE = ClassificationTemplate(
    rails=["within_scope", "out_of_scope"],
    template="""
You are evaluating whether an AI assistant handled a question about the Texas Flood
Knowledge Graph appropriately.

The knowledge graph contains: NOAA Storm Events, FEMA Disaster Declarations,
ACS demographic/economic indicators, and NWS flash flood warnings for Texas counties.
It does NOT contain: NFIP flood insurance claims, property values, river gauge
readings, forecasts, or data from outside Texas.

Question:
{input}

Assistant's answer:
{output}

Instructions:
- Answer WITHIN_SCOPE if:
    (a) the question is answerable from the graph and the assistant attempted to
        answer it using the available tools and data, OR
    (b) the question asks for something not in the graph (e.g. NFIP claims) and
        the assistant clearly stated the data is not available.
- Answer OUT_OF_SCOPE if:
    (a) the assistant attempted to answer a question that cannot be answered from
        this graph (e.g. fabricated NFIP numbers), OR
    (b) the assistant refused a question that is clearly answerable from the graph.

Respond with exactly one of: within_scope or out_of_scope.
""".strip(),
    scores=[1, 0],
)


def check_answer_scope(input, output) -> str:  # noqa: A002
    """Score whether agent answered in-scope questions and refused out-of-scope ones."""
    llm = OpenAIModel(
        model=_JUDGE_MODEL,
        base_url=_BASE_URL,
        api_key=_API_KEY,
        temperature=0.0,
    )
    classifier = LLMClassifier(
        name="scope",
        template=_TEMPLATE,
        llm=llm,
        provide_explanation=False,
    )
    result = classifier(
        input=str(input.get("query", input)),
        output=str(output),
    )
    return result[0]
