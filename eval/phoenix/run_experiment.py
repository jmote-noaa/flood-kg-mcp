"""
run_experiment.py — Run flood-kg-eval experiments against Phoenix datasets.

Supports multiple agent models in a single invocation (sequential).

Usage:
    # Single model (default from .env AGENT_MODEL):
    uv run run_experiment.py --dataset-name flood-eval-0

    # Multiple models, compared side-by-side in Phoenix:
    uv run run_experiment.py --dataset-name flood-eval-0 `
        --agent-model <model-id-1> --agent-model <model-id-2>

    # v2 prompt (schema inlined):
    uv run run_experiment.py --dataset-name flood-eval-0 --system-prompt-version v2

    # Skip CSV pre-flight check:
    uv run run_experiment.py --dataset-name flood-eval-0 --no-validate

Run from eval/phoenix/ after: uv sync --group dev
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

EVAL_DIR = Path(__file__).parent
DATASETS_YAML = EVAL_DIR / "datasets.yaml"

sys.path.insert(0, str(EVAL_DIR))


def load_registry() -> dict:
    with open(DATASETS_YAML, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["datasets"]


def run_for_model(
    *,
    model: str,
    dataset_name: str,
    system_prompt_version: str,
    project_name: str,
    phoenix_endpoint: str,
    experiment_description: str | None,
    dataset_version_id: str | None,
) -> None:
    """Run the full dataset against a single model and log to Phoenix."""
    from agent import FloodKGAgent
    from judges import check_answer_scope, match_expected_response
    from phoenix.client import Client

    print(f"\n{'='*60}")
    print(f"  Model  : {model}")
    print(f"  Prompt : system_prompt_{system_prompt_version}.txt")
    print(f"  Dataset: {dataset_name}")
    print(f"{'='*60}")

    agent = FloodKGAgent(system_prompt_version=system_prompt_version, model=model)
    agent.initialize(project_name=project_name, phoenix_endpoint=phoenix_endpoint)

    client = Client(base_url=phoenix_endpoint)
    get_kwargs: dict = {"dataset": dataset_name}
    if dataset_version_id:
        get_kwargs["version_id"] = dataset_version_id
    dataset = client.datasets.get_dataset(**get_kwargs)

    exp_description = experiment_description or (
        f"prompt={system_prompt_version} model={model}"
    )
    # Slashes in experiment names can cause display issues; use __ as separator.
    exp_name = f"{dataset_name}__{system_prompt_version}__{model}"

    client.experiments.run_experiment(
        dataset=dataset,
        task=agent.create_experiment_task(),
        evaluators=[check_answer_scope, match_expected_response],
        experiment_name=exp_name,
        experiment_description=exp_description,
    )
    print(f"  Done. View results at {phoenix_endpoint}")


def main() -> None:
    registry = load_registry()
    default_model = os.getenv("AGENT_MODEL", "")

    parser = argparse.ArgumentParser(description="Run flood-kg eval experiments.")
    parser.add_argument(
        "--dataset-name",
        required=True,
        choices=list(registry),
        help="Dataset name from datasets.yaml",
    )
    parser.add_argument(
        "--agent-model",
        action="append",
        dest="agent_models",
        metavar="MODEL",
        help="USAi model id to evaluate (repeatable). "
             "Defaults to AGENT_MODEL from .env.",
    )
    parser.add_argument(
        "--system-prompt-version",
        default="v1",
        choices=["v1", "v2"],
        help="Prompt version (default: v1)",
    )
    parser.add_argument("--project-name", default="flood-kg-eval")
    parser.add_argument("--phoenix-endpoint", default="http://localhost:6006")
    parser.add_argument(
        "--experiment-description",
        help="Override the auto-generated experiment description",
    )
    parser.add_argument(
        "--dataset-version-id",
        help="Pin a specific Phoenix dataset version id",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip CSV pre-flight check before running",
    )
    args = parser.parse_args()

    models: list[str] = args.agent_models or ([default_model] if default_model else [])
    if not models:
        parser.error(
            "No model specified. Use --agent-model or set AGENT_MODEL in .env."
        )

    if not args.no_validate:
        meta = registry[args.dataset_name]
        csv_path = EVAL_DIR / meta["csv_path"]
        if not csv_path.exists():
            print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
            sys.exit(1)
        print(f"CSV validated: {csv_path}")

    for model in models:
        run_for_model(
            model=model,
            dataset_name=args.dataset_name,
            system_prompt_version=args.system_prompt_version,
            project_name=args.project_name,
            phoenix_endpoint=args.phoenix_endpoint,
            experiment_description=args.experiment_description,
            dataset_version_id=args.dataset_version_id,
        )


if __name__ == "__main__":
    main()
