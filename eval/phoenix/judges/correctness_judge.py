"""
correctness_judge — LLM-as-judge: does the agent answer match the expected facts?

Returns "correct" or "incorrect".
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
- Numbers: treat values as matching if they agree after reasonable rounding
  (e.g., 3.36 vs 3.4 hours; 33.5% vs 0.335). Counts must match exactly.
- Ranked lists: correct if most of the reference items (at least 80%) appear,
  with the top-ranked items in roughly the same order. Extra items beyond
  the reference are acceptable.
- Multi-part answers (e.g., several separate rankings): each part must be
  present and substantially correct.
- If the reference says a measure is unsupported or the data is not in the
  graph: correct only if the assistant declines and explains why. Incorrect
  if it produces a number, score, or index anyway.
- Optional caveats in the reference (e.g., small-population notes) are not
  required.
- Incorrect if key facts are missing, values are wrong, or the assistant
  declines when the reference gives a clear answer.

Respond with exactly one word: correct or incorrect.
""".strip(),
    scores=[1, 0],
)


def match_expected_response(input, output, expected) -> str:  # noqa: A002
    """Score agent output against the ground-truth reference answer."""
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
        name="correctness",
        template=_TEMPLATE,
        llm=llm,
        provide_explanation=True,
    )
    result = classifier(
        input=str(input.get("query", input)),
        output=str(output),
        reference=str(expected.get("responses", "")),
    )
    return result[0]
