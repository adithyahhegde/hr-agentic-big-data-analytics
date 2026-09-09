"""Validate Spark descriptive analytics against a configured external Spark master.

This is an opt-in target-environment protocol. It never invents cluster results:
without HR_ANALYTICS_SPARK_MASTER the command exits with a clear configuration
error. Use a master such as spark://host:7077 in an environment that can reach it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

from app.services.analytics import analyze_csv
from app.services.spark_analytics import analyze_spark_csv_lines

try:
    from scripts.benchmark import MAPPINGS, make_fixture
except ModuleNotFoundError:
    from benchmark import MAPPINGS, make_fixture

DEFAULT_SIZES = (100, 1_000, 10_000)
MAX_VALIDATION_ROWS = 100_000
PROTOCOL_VERSION = "external_spark_scalability_v2"
NUMERIC_ABS_TOLERANCE = 1e-9
NUMERIC_REL_TOLERANCE = 1e-6


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
    if any(size > MAX_VALIDATION_ROWS for size in normalized):
        raise ValueError(f"sizes must not exceed {MAX_VALIDATION_ROWS:,} rows")
    return normalized


def _aggregate_signature(result: dict[str, Any]) -> dict[str, Any]:
    numeric = []
    for item in result.get("numeric_summary", []):
        numeric.append({key: item.get(key) for key in ("field", "count", "min", "max", "mean")})
    categorical = []
    for item in result.get("categorical_summary", []):
        top_values = sorted(
            ({"value": value.get("value"), "count": value.get("count"), "share": value.get("share")} for value in item.get("top_values", [])),
            key=lambda value: (str(value["value"]), value["count"] or 0),
        )
        categorical.append({
            "field": item.get("field"),
            "count": item.get("count"),
            "distinct": item.get("distinct"),
            "top_values": top_values,
        })
    return {
        "row_count": result.get("row_count"),
        "duplicate_row_count": result.get("duplicate_row_count"),
        "numeric_summary": sorted(numeric, key=lambda item: item["field"] or ""),
        "categorical_summary": sorted(categorical, key=lambda item: item["field"] or ""),
        "missing_by_field": sorted(result.get("missing_by_field", []), key=lambda item: item.get("field", "")),
    }


def _aggregate_values_match(actual: Any, expected: Any) -> bool:
    """Compare aggregate payloads while allowing harmless floating-point drift."""
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            _aggregate_values_match(actual[key], expected[key]) for key in expected
        )
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _aggregate_values_match(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected)
        )
    if isinstance(actual, float) or isinstance(expected, float):
        if actual is None or expected is None:
            return actual is expected
        return math.isclose(float(actual), float(expected), rel_tol=NUMERIC_REL_TOLERANCE, abs_tol=NUMERIC_ABS_TOLERANCE)
    return actual == expected


def _validate_result(result: dict[str, Any], rows: int, expected_aggregates: dict[str, Any] | None = None) -> dict[str, Any]:
    execution = result.get("execution", {})
    validation: dict[str, Any] = {
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
    if expected_aggregates is not None:
        aggregate_fields = {"duplicate_row_count", "numeric_summary", "categorical_summary", "missing_by_field"}
        if not aggregate_fields.issubset(result):
            missing = sorted(aggregate_fields.difference(result))
            raise RuntimeError(f"external Spark result is missing required aggregate fields: {', '.join(missing)}")
        actual = _aggregate_signature(result)
        validation["aggregates_match_local_baseline"] = _aggregate_values_match(actual, expected_aggregates)
        if not validation["aggregates_match_local_baseline"]:
            raise RuntimeError("external Spark aggregates differ from the deterministic local baseline")
    return validation


def validate(*, rows: int = 10_000, seed: int = 42, master: str | None = None) -> dict[str, Any]:
    if rows < 1:
        raise ValueError("rows must be positive")
    return validate_sizes(sizes=(rows,), seed=seed, master=master, protocol=PROTOCOL_VERSION)["runs"][0]


def validate_sizes(*, sizes: Sequence[int] = DEFAULT_SIZES, seed: int = 42, master: str | None = None, protocol: str = PROTOCOL_VERSION) -> dict[str, Any]:
    normalized_sizes = _validate_sizes(sizes)
    configured_master = _validate_external_master(master)
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    runs: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="hr_external_spark_") as tmp:
        for rows in normalized_sizes:
            path = Path(tmp) / f"fixture-{rows}.csv"
            make_fixture(path, rows, seed, "clean")
            fixture_bytes = path.read_bytes()
            fixture_sha256 = hashlib.sha256(fixture_bytes).hexdigest()
            fixture_schema = list(path.read_text(encoding="utf-8").splitlines()[0].split(","))
            expected_aggregates = _aggregate_signature(analyze_csv(path, MAPPINGS))
            started = time.perf_counter()
            lines = fixture_bytes.decode("utf-8").splitlines()
            result = analyze_spark_csv_lines(lines, MAPPINGS, master=configured_master, stop_session=True)
            elapsed = time.perf_counter() - started
            validation = _validate_result(result, rows, expected_aggregates)
            runs.append({
                "rows": rows,
                "fixture_sha256": fixture_sha256,
                "fixture_schema": fixture_schema,
                "elapsed_seconds": round(elapsed, 6),
                "rows_per_second": round(rows / elapsed, 3) if elapsed > 0 else None,
                "result": result,
                "validation": validation,
            })
    return {
        "protocol": protocol,
        "sizes": normalized_sizes,
        "seed": seed,
        "started_at": started_at,
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
