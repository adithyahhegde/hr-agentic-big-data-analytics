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
import platform
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
    sizes_list = list(sizes)
    if not sizes_list or any(not isinstance(size, int) or isinstance(size, bool) or size < 1 for size in sizes_list):
        raise ValueError("sizes must contain positive integers")
    if len(set(sizes_list)) != len(sizes_list):
        raise ValueError("sizes must be unique so the scalability evidence matches the requested protocol")
    if any(size > MAX_VALIDATION_ROWS for size in sizes_list):
        raise ValueError(f"sizes must not exceed {MAX_VALIDATION_ROWS:,} rows")
    return sorted(sizes_list)


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
    missing_by_field = [item for item in result.get("missing_by_field", []) if item.get("missing", 0) != 0]
    return {
        "row_count": result.get("row_count"),
        "duplicate_row_count": result.get("duplicate_row_count"),
        "numeric_summary": sorted(numeric, key=lambda item: item["field"] or ""),
        "categorical_summary": sorted(categorical, key=lambda item: item["field"] or ""),
        "missing_by_field": sorted(missing_by_field, key=lambda item: item.get("field", "")),
    }


def _aggregate_values_match(actual: Any, expected: Any) -> bool:
    if isinstance(actual, dict) and isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_aggregate_values_match(actual[key], expected[key]) for key in expected)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(_aggregate_values_match(a, e) for a, e in zip(actual, expected))
    if isinstance(actual, float) or isinstance(expected, float):
        if actual is None or expected is None:
            return actual is expected
        return math.isclose(float(actual), float(expected), rel_tol=NUMERIC_REL_TOLERANCE, abs_tol=NUMERIC_ABS_TOLERANCE)
    return actual == expected


def _first_aggregate_difference(actual: Any, expected: Any, path: str = "root") -> str | None:
    if isinstance(actual, dict) and isinstance(expected, dict):
        if actual.keys() != expected.keys():
            return f"{path}: keys differ (actual={sorted(actual)}, expected={sorted(expected)})"
        for key in expected:
            difference = _first_aggregate_difference(actual[key], expected[key], f"{path}.{key}")
            if difference:
                return difference
        return None
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return f"{path}: list lengths differ (actual={len(actual)}, expected={len(expected)})"
        for index, (actual_item, expected_item) in enumerate(zip(actual, expected)):
            difference = _first_aggregate_difference(actual_item, expected_item, f"{path}[{index}]")
            if difference:
                return difference
        return None
    if isinstance(actual, float) or isinstance(expected, float):
        if actual is None or expected is None:
            return None if actual is expected else f"{path}: actual={actual!r}, expected={expected!r}"
        if math.isclose(float(actual), float(expected), rel_tol=NUMERIC_REL_TOLERANCE, abs_tol=NUMERIC_ABS_TOLERANCE):
            return None
    elif actual == expected:
        return None
    return f"{path}: actual={actual!r}, expected={expected!r}"


def _validate_result(result: dict[str, Any], rows: int, expected_aggregates: dict[str, Any] | None = None, expected_spark_version: str | None = None) -> dict[str, Any]:
    execution = result.get("execution", {})
    validation: dict[str, Any] = {
        "row_count_matches_fixture": result.get("row_count") == rows,
        "raw_rows_returned": execution.get("raw_rows_returned"),
        "distributed": execution.get("distributed"),
        "spark_version_present": bool(execution.get("spark_version")),
        "parallelism_positive": isinstance(execution.get("default_parallelism"), int) and execution.get("default_parallelism", 0) > 0,
        "application_id_present": bool(execution.get("application_id")),
    }
    if not validation["row_count_matches_fixture"]:
        raise RuntimeError("external Spark validation returned an unexpected row count")
    if validation["distributed"] is not True:
        raise RuntimeError("configured non-local Spark master did not report distributed execution")
    if validation["raw_rows_returned"] is not False:
        raise RuntimeError("external Spark validation must not return raw rows")
    if not validation["spark_version_present"]:
        raise RuntimeError("external Spark validation did not report the target Spark version")
    if expected_spark_version and execution.get("spark_version") != expected_spark_version:
        raise RuntimeError(f"external Spark version contract failed: target={execution.get('spark_version')!r}, expected={expected_spark_version!r}")
    if expected_aggregates is not None:
        aggregate_fields = {"duplicate_row_count", "numeric_summary", "categorical_summary", "missing_by_field"}
        if not aggregate_fields.issubset(result):
            missing = sorted(aggregate_fields.difference(result))
            raise RuntimeError(f"external Spark result is missing required aggregate fields: {', '.join(missing)}")
        actual = _aggregate_signature(result)
        validation["aggregates_match_local_baseline"] = _aggregate_values_match(actual, expected_aggregates)
        if not validation["aggregates_match_local_baseline"]:
            difference = _first_aggregate_difference(actual, expected_aggregates) or "unknown aggregate difference"
            raise RuntimeError(f"external Spark aggregates differ from the deterministic local baseline: {difference}")
    return validation


def _scaling_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Record descriptive adjacent-size scaling factors without imposing a performance threshold."""
    comparisons: list[dict[str, Any]] = []
    for previous, current in zip(runs, runs[1:]):
        row_growth = current["rows"] / previous["rows"]
        elapsed_growth = current["elapsed_seconds"] / previous["elapsed_seconds"]
        throughput_growth = current["rows_per_second"] / previous["rows_per_second"]
        comparisons.append({
            "from_rows": previous["rows"],
            "to_rows": current["rows"],
            "row_growth_factor": round(row_growth, 6),
            "elapsed_growth_factor": round(elapsed_growth, 6),
            "throughput_growth_factor": round(throughput_growth, 6),
        })
    summary: dict[str, Any] = {"adjacent_comparisons": comparisons}
    if len(runs) >= 2:
        summary["largest_to_smallest_elapsed_ratio"] = round(runs[-1]["elapsed_seconds"] / runs[0]["elapsed_seconds"], 6)
        summary["largest_to_smallest_throughput_ratio"] = round(runs[-1]["rows_per_second"] / runs[0]["rows_per_second"], 6)
    return summary


def validate(*, rows: int = 10_000, seed: int = 42, master: str | None = None) -> dict[str, Any]:
    normalized_rows = _validate_sizes((rows,))[0]
    return validate_sizes(sizes=(normalized_rows,), seed=seed, master=master, protocol=PROTOCOL_VERSION)["runs"][0]


def validate_sizes(*, sizes: Sequence[int] = DEFAULT_SIZES, seed: int = 42, master: str | None = None, protocol: str = PROTOCOL_VERSION) -> dict[str, Any]:
    normalized_sizes = _validate_sizes(sizes)
    configured_master = _validate_external_master(master)
    expected_spark_version = os.getenv("SPARK_VALIDATION_VERSION", "").strip() or None
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    source_revision = os.getenv("GITHUB_SHA") or os.getenv("HR_ANALYTICS_SOURCE_REVISION") or "unknown"
    runtime = {"python_version": platform.python_version(), "platform": platform.platform()}
    target_fingerprint = hashlib.sha256(configured_master.encode("utf-8")).hexdigest()
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
            validation = _validate_result(result, rows, expected_aggregates, expected_spark_version)
            if elapsed <= 0:
                raise RuntimeError("external Spark validation produced a non-positive elapsed time")
            runs.append({
                "rows": rows,
                "fixture_sha256": fixture_sha256,
                "fixture_schema": fixture_schema,
                "elapsed_seconds": round(elapsed, 6),
                "rows_per_second": round(rows / elapsed, 3),
                "result": result,
                "validation": validation,
            })
    return {
        "protocol": protocol,
        "sizes": normalized_sizes,
        "seed": seed,
        "started_at": started_at,
        "source_revision": source_revision,
        "runtime": runtime,
        "master_kind": configured_master.split(":", 1)[0],
        "target_fingerprint": target_fingerprint,
        "runs": runs,
        "scaling": _scaling_summary(runs),
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
