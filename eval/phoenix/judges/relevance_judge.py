"""
relevance_judge — LLM-as-judge: did the agent handle the question appropriately?

Returns "appropriate" or "inappropriate".
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from phoenix.evals import ClassificationTemplate, LLMClassifier, OpenAIModel

load_dotenv()

_BASE_URL = os.getenv("USAI_BASE_URL", "").rstrip("/")
if not _BASE_URL.endswith("/api/v1"):
    _BASE_URL = _BASE_URL + "/api/v1"
_API_KEY = os.getenv("USAI_API_KEY", "")

_TEMPLATE = ClassificationTemplate(
    rails=["appropriate", "inappropriate"],
    template="""
You are evaluating whether an AI assistant handled a question about the Texas Flood
Knowledge Graph appropriately.

The knowledge graph contains: NOAA Storm Events (including property damage),
FEMA Disaster Declarations, ACS demographic/economic indicators, and NWS flash
flood warnings for Texas counties.
It does NOT contain: NFIP flood insurance claims, real-estate property values
(Storm Events property damage is included), river gauge readings, forecasts,
or data from outside Texas.

Question:
{input}

Assistant's answer:
{output}

Instructions:
- Answer APPROPRIATE if:
    (a) the question is answerable from the graph and the assistant attempted to
        answer it using the available tools and data, OR
    (b) the question asks for something not in the graph (e.g. NFIP claims) and
        the assistant clearly stated the data is not available, OR
    (c) the question asks for a composite index, score, or ranking that combines
        several indicators (e.g., a "resilience score") — this is not a supported
        construct; declining and offering the individual indicators instead is
        APPROPRIATE. Building such a score is INAPPROPRIATE.
- Answer INAPPROPRIATE if:
    (a) the assistant attempted to answer a question that cannot be answered from
        this graph (e.g. fabricated NFIP numbers, or built an unsupported composite
        index), OR
    (b) the assistant refused a question that is clearly answerable from the graph.

Respond with exactly one of: appropriate or inappropriate.
""".strip(),
    scores=[1, 0],
)


def check_answer_scope(input, output) -> str:  # noqa: A002
    """Score whether agent handled questions appropriately."""
    judge_model = os.getenv("JUDGE_MODEL", "")
    if not judge_model:
        raise RuntimeError(
            "JUDGE_MODEL is not set. Add it to .env before running evaluations. "
            "Use a strong model separate from AGENT_MODEL to avoid self-preference "
            "bias."
        )
    llm = OpenAIModel(
        model=judge_model,
        base_url=_BASE_URL,
        api_key=_API_KEY,
        temperature=0.0,
    )
    classifier = LLMClassifier(
        name="scope",
        template=_TEMPLATE,
        llm=llm,
        provide_explanation=True,
    )
    result = classifier(
        input=str(input.get("query", input)),
        output=str(output),
    )
    return result[0]
