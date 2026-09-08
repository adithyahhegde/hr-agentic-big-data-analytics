"""Validate Spark descriptive analytics against a configured external Spark master.

This is an opt-in target-environment protocol. It never invents cluster results:
without HR_ANALYTICS_SPARK_MASTER the command exits with a clear configuration
error. Use a master such as spark://host:7077 in an environment that can reach it.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from app.services.spark_analytics import analyze_spark

try:
    from scripts.benchmark import MAPPINGS, make_fixture
except ModuleNotFoundError:  # Supports direct execution from the repository root.
    from benchmark import MAPPINGS, make_fixture


def validate(*, rows: int = 10_000, seed: int = 42, master: str | None = None) -> dict[str, Any]:
    if rows < 1:
        raise ValueError("rows must be positive")
    configured_master = master or os.getenv("HR_ANALYTICS_SPARK_MASTER")
    if not configured_master:
        raise ValueError("HR_ANALYTICS_SPARK_MASTER must be set for external Spark validation")
    if configured_master.startswith("local"):
        raise ValueError("external Spark validation requires a non-local Spark master")

    with tempfile.TemporaryDirectory(prefix="hr_external_spark_") as tmp:
        path = Path(tmp) / "fixture.csv"
        make_fixture(path, rows, seed, "clean")
        result = analyze_spark(path, MAPPINGS, master=configured_master)

    return {
        "protocol": "external_spark_validation_v1",
        "rows": rows,
        "seed": seed,
        "master_kind": configured_master.split(":", 1)[0],
        "result": result,
        "validation": {
            "row_count_matches_fixture": result.get("row_count") == rows,
            "raw_rows_returned": result.get("execution", {}).get("raw_rows_returned"),
            "distributed": result.get("execution", {}).get("distributed"),
        },
        "limitation": "Results depend on the configured target Spark cluster, worker resources, Spark version, and network/filesystem configuration.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--master")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(rows=args.rows, seed=args.seed, master=args.master)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
