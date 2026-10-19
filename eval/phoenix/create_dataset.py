"""
create_dataset.py — Upload a flood-eval CSV dataset to Phoenix.

Usage:
    uv run create_dataset.py --dataset-name flood-eval-0
    uv run create_dataset.py --dataset-name flood-eval-0 --dry-run
    uv run create_dataset.py --list
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

EVAL_DIR = Path(__file__).parent
DATASETS_YAML = EVAL_DIR / "datasets.yaml"


def load_registry() -> dict:
    with open(DATASETS_YAML, encoding="utf-8") as fh:
        return yaml.safe_load(fh)["datasets"]


def list_datasets(registry: dict) -> None:
    print("Available datasets:")
    for name, meta in registry.items():
        print(f"  {name}: {meta.get('description', '')}")
        print(f"    csv: {meta['csv_path']}")


def validate_csv(
    csv_path: Path, input_keys: list[str], output_keys: list[str]
) -> list[dict]:
    if not csv_path.exists():
        print(f"ERROR: CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    required = set(input_keys) | set(output_keys)
    rows = []
    with open(csv_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = required - set(reader.fieldnames or [])
        if missing:
            print(f"ERROR: CSV missing columns: {missing}", file=sys.stderr)
            sys.exit(1)
        for row in reader:
            rows.append(row)
    print(f"  Validated {len(rows)} rows — columns OK: {sorted(required)}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload eval dataset to Phoenix.")
    parser.add_argument("--dataset-name", help="Dataset name from datasets.yaml")
    parser.add_argument(
        "--phoenix-name",
        help="Override Phoenix dataset name (default: dataset-name)",
    )
    parser.add_argument("--csv-path", help="Override CSV path from datasets.yaml")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate only, no upload"
    )
    parser.add_argument(
        "--list", action="store_true", help="List available datasets and exit"
    )
    parser.add_argument("--phoenix-endpoint", default="http://localhost:6006")
    args = parser.parse_args()

    registry = load_registry()

    if args.list:
        list_datasets(registry)
        return

    if not args.dataset_name:
        parser.error("--dataset-name is required (or use --list)")

    if args.dataset_name not in registry:
        print(
            f"ERROR: '{args.dataset_name}' not in datasets.yaml. Use --list.",
            file=sys.stderr,
        )
        sys.exit(1)

    meta = registry[args.dataset_name]
    csv_path = Path(args.csv_path) if args.csv_path else EVAL_DIR / meta["csv_path"]
    input_keys: list[str] = meta["input_keys"]
    output_keys: list[str] = meta["output_keys"]
    phoenix_name = args.phoenix_name or args.dataset_name

    print(f"Dataset : {args.dataset_name}")
    print(f"CSV     : {csv_path}")
    validate_csv(csv_path, input_keys, output_keys)

    if args.dry_run:
        print("Dry run — skipping upload.")
        return

    from phoenix.client import Client

    client = Client(base_url=args.phoenix_endpoint)
    client.datasets.create_dataset(
        name=phoenix_name,
        csv_file_path=csv_path,
        input_keys=input_keys,
        output_keys=output_keys,
        dataset_description=meta.get("description", ""),
    )
    print(
        f"Uploaded '{phoenix_name}' ({args.phoenix_endpoint})"
    )


if __name__ == "__main__":
    main()
