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
import time
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

from app.services.spark_analytics import analyze_spark_csv_lines

try:
    from scripts.benchmark import MAPPINGS, make_fixture
except ModuleNotFoundError:  # Supports direct execution from the repository root.
    from benchmark import MAPPINGS, make_fixture

DEFAULT_SIZES = (100, 1_000, 10_000)


def _validate_external_master(master: str | None) -> str:
    configured_master = (master or os.getenv("HR_ANALYTICS_SPARK_MASTER") or "").strip()
    if not configured_master:
        raise ValueError("HR_ANALYTICS_SPARK_MASTER must be set for external Spark validation")
    if configured_master.startswith("local"):
        raise ValueError("external Spark validation requires a non-local Spark master")
    try:
        parsed = urlsplit(configured_master)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise ValueError("external Spark validation requires a master like spark://host:7077") from error
    if parsed.scheme != "spark" or not hostname or port is None:
        raise ValueError("external Spark validation requires a master like spark://host:7077")
    if hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("external Spark validation requires a non-loopback Spark master")
    return configured_master


def _validate_sizes(sizes: Sequence[int]) -> list[int]:
    normalized = sorted(set(sizes))
    if not normalized or any(size < 1 for size in normalized):
        raise ValueError("sizes must contain positive integers")
    return normalized


def _validate_result(result: dict[str, Any], rows: int) -> dict[str, bool]:
    execution = result.get("execution", {})
    validation = {
        "row_count_matches_fixture": result.get("row_count") == rows,
        "raw_rows_returned": execution.get("raw_rows_returned"),
        "distributed": execution.get("distributed"),
    }
    if not validation["row_count_matches_fixture"]:
        raise RuntimeError("external Spark validation returned an unexpected row count")
    if validation["distributed"] is not True:
        raise RuntimeError("configured non-local Spark master did not report distributed execution")
    if validation["raw_rows_returned"] is not False:
        raise RuntimeError("external Spark validation must not return raw rows")
    return validation


def validate(*, rows: int = 10_000, seed: int = 42, master: str | None = None) -> dict[str, Any]:
    """Run the legacy single-size protocol and retain its result shape."""
    if rows < 1:
        raise ValueError("rows must be positive")
    return validate_sizes(sizes=(rows,), seed=seed, master=master, protocol="external_spark_validation_v1")["runs"][0]


def validate_sizes(
    *,
    sizes: Sequence[int] = DEFAULT_SIZES,
    seed: int = 42,
    master: str | None = None,
    protocol: str = "external_spark_scalability_v1",
) -> dict[str, Any]:
    """Measure the bounded descriptive path at multiple target-cluster sizes.

    Only aggregate results are retained. Each size gets a fresh deterministic
    fixture. CSV content is transferred to the target Spark application through
    an RDD so validation does not depend on executor access to a driver-local
    temporary filesystem.
    """
    normalized_sizes = _validate_sizes(sizes)
    configured_master = _validate_external_master(master)
    runs: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="hr_external_spark_") as tmp:
        for rows in normalized_sizes:
            path = Path(tmp) / f"fixture-{rows}.csv"
            make_fixture(path, rows, seed, "clean")
            started = time.perf_counter()
            lines = path.read_text(encoding="utf-8").splitlines()
            result = analyze_spark_csv_lines(lines, MAPPINGS, master=configured_master)
            elapsed = time.perf_counter() - started
            validation = _validate_result(result, rows)
            runs.append({
                "rows": rows,
                "elapsed_seconds": round(elapsed, 6),
                "rows_per_second": round(rows / elapsed, 3) if elapsed > 0 else None,
                "result": result,
                "validation": validation,
            })

    return {
        "protocol": protocol,
        "sizes": normalized_sizes,
        "seed": seed,
        "master_kind": configured_master.split(":", 1)[0],
        "runs": runs,
        "limitation": "Results depend on the configured target Spark cluster, worker resources, Spark version, and network/filesystem configuration. Wall-clock measurements are target-environment evidence, not universal performance guarantees.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=None, help="Legacy single-size run; prefer --sizes for scalability evidence")
    parser.add_argument("--sizes", type=int, nargs="+", default=None, help="Target-cluster fixture sizes (default: 100 1000 10000)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--master")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.rows is not None and args.sizes is not None:
        parser.error("use either --rows or --sizes, not both")
    sizes = (args.rows,) if args.rows is not None else (args.sizes or DEFAULT_SIZES)
    result = validate_sizes(sizes=sizes, seed=args.seed, master=args.master)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
