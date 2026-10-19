"""
correctness_judge — LLM-as-judge: does the agent answer match the expected facts?

Returns "correct" or "incorrect".
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
    rails=["correct", "incorrect"],
    template="""
You are evaluating whether an AI assistant's answer correctly addresses a question
about the Texas Flood Knowledge Graph.

Question:
{input}

Reference answer (the ground truth):
{reference}

Assistant's answer:
{output}

Instructions:
- The assistant's answer is CORRECT if it contains the key facts from the reference
  answer. Minor differences in wording, formatting, units, or surrounding context
  are acceptable.
- The assistant's answer is INCORRECT if it is missing key facts, states wrong
  values, or refuses to answer when the reference provides a clear answer.
- For refusal cases (Q9) and out-of-scope cases (Q10): the answer is CORRECT if
  the assistant declines appropriately and explains why, even if the wording differs.

Respond with exactly one word: correct or incorrect.
""".strip(),
    scores=[1, 0],
)


def match_expected_response(input, output, expected) -> str:  # noqa: A002
    """Score agent output against the ground-truth reference answer."""
    llm = OpenAIModel(
        model=_JUDGE_MODEL,
        base_url=_BASE_URL,
        api_key=_API_KEY,
        temperature=0.0,
    )
    classifier = LLMClassifier(
        name="correctness",
        template=_TEMPLATE,
        llm=llm,
        provide_explanation=False,
    )
    result = classifier(
        input=str(input.get("query", input)),
        output=str(output),
        reference=str(expected.get("responses", "")),
    )
    return result[0]
