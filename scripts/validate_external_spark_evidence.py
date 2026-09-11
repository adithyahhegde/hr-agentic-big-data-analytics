"""Validate provenance and bounded aggregate evidence in an external Spark artifact.

This intentionally validates metadata and aggregate validation flags only; it never
inspects or prints employee rows.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

SOURCE_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
HEX_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_PROTOCOL = "external_spark_scalability_v2"
EXPECTED_SEED = 42
EXPECTED_INPUT_MODE = "driver_parallelized_csv"


def _finite_number(value: object, *, name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def validate_evidence(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("protocol") != EXPECTED_PROTOCOL:
        raise ValueError(f"evidence protocol must be {EXPECTED_PROTOCOL}")
    if data.get("seed") != EXPECTED_SEED:
        raise ValueError(f"evidence seed must be {EXPECTED_SEED}")
    sizes = data.get("sizes")
    if not isinstance(sizes, list) or not sizes or any(not isinstance(size, int) or isinstance(size, bool) or size <= 0 for size in sizes):
        raise ValueError("evidence sizes must be a non-empty list of positive integers")
    if sizes != sorted(sizes) or len(sizes) != len(set(sizes)):
        raise ValueError("evidence sizes must be sorted and unique")

    source_revision = data.get("source_revision")
    if not isinstance(source_revision, str) or not SOURCE_REVISION_RE.fullmatch(source_revision):
        raise ValueError("evidence source_revision must be a 40-character lowercase Git commit SHA")
    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("evidence runtime provenance is required")
    for key in ("python_version", "platform"):
        if not isinstance(runtime.get(key), str) or not runtime[key].strip():
            raise ValueError(f"evidence runtime.{key} is required")

    target_fingerprint = data.get("target_fingerprint")
    if not isinstance(target_fingerprint, str) or not HEX_SHA256_RE.fullmatch(target_fingerprint):
        raise ValueError("evidence target_fingerprint must be a 64-character lowercase SHA-256")

    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("evidence must contain at least one run")
    if [run.get("rows") for run in runs] != sizes:
        raise ValueError("evidence run row counts must exactly match sizes")

    for run in runs:
        fingerprint = run.get("fixture_sha256")
        if not isinstance(fingerprint, str) or not HEX_SHA256_RE.fullmatch(fingerprint):
            raise ValueError("each evidence run requires a 64-character lowercase fixture_sha256")
        if not isinstance(run.get("fixture_schema"), list) or not run["fixture_schema"]:
            raise ValueError("each evidence run requires a non-empty fixture_schema")
        elapsed = _finite_number(run.get("elapsed_seconds"), name="elapsed_seconds")
        throughput = _finite_number(run.get("rows_per_second"), name="rows_per_second")
        if elapsed < 0:
            raise ValueError("each evidence run requires non-negative elapsed_seconds")
        if throughput <= 0:
            raise ValueError("each evidence run requires positive rows_per_second")

        validation = run.get("validation")
        if not isinstance(validation, dict):
            raise ValueError("each evidence run requires validation metadata")
        for key in (
            "row_count_matches_fixture",
            "distributed",
            "raw_rows_returned",
            "aggregates_match_local_baseline",
            "spark_version_present",
            "parallelism_positive",
            "application_id_present",
        ):
            if not isinstance(validation.get(key), bool):
                raise ValueError(f"each evidence run requires boolean validation.{key}")
        if not validation["row_count_matches_fixture"]:
            raise ValueError("evidence row-count validation must pass")
        if not validation["distributed"]:
            raise ValueError("evidence distributed-execution validation must pass")
        if validation["raw_rows_returned"]:
            raise ValueError("evidence must not report raw rows returned")
        if not validation["aggregates_match_local_baseline"]:
            raise ValueError("evidence aggregate validation must pass")
        if not validation["spark_version_present"] or not validation["parallelism_positive"] or not validation["application_id_present"]:
            raise ValueError("evidence Spark execution provenance validation must pass")

        execution = run.get("result", {}).get("execution")
        if not isinstance(execution, dict):
            raise ValueError("each evidence run requires execution provenance")
        if not isinstance(execution.get("spark_version"), str) or not execution["spark_version"].strip():
            raise ValueError("each evidence run requires execution.spark_version")
        if not isinstance(execution.get("default_parallelism"), int) or isinstance(execution.get("default_parallelism"), bool) or execution["default_parallelism"] <= 0:
            raise ValueError("each evidence run requires positive execution.default_parallelism")
        if not isinstance(execution.get("application_id"), str) or not execution["application_id"].strip():
            raise ValueError("each evidence run requires execution.application_id")
        if execution.get("input_mode") != EXPECTED_INPUT_MODE:
            raise ValueError(f"evidence input_mode must be {EXPECTED_INPUT_MODE}")

    scaling = data.get("scaling")
    if not isinstance(scaling, dict):
        raise ValueError("evidence scaling summary is required")
    comparisons = scaling.get("adjacent_comparisons")
    if not isinstance(comparisons, list) or len(comparisons) != max(0, len(runs) - 1):
        raise ValueError("evidence scaling adjacent_comparisons must match the number of benchmark intervals")
    for index, comparison in enumerate(comparisons):
        if not isinstance(comparison, dict):
            raise ValueError("each evidence scaling comparison must be an object")
        expected_from = runs[index]["rows"]
        expected_to = runs[index + 1]["rows"]
        if comparison.get("from_rows") != expected_from or comparison.get("to_rows") != expected_to:
            raise ValueError("evidence scaling comparison row bounds do not match benchmark runs")
        for key in ("row_growth_factor", "elapsed_growth_factor", "throughput_growth_factor"):
            value = _finite_number(comparison.get(key), name=f"scaling.{key}")
            if value <= 0:
                raise ValueError(f"scaling.{key} must be positive")
    if len(runs) >= 2:
        for key in ("largest_to_smallest_elapsed_ratio", "largest_to_smallest_throughput_ratio"):
            value = _finite_number(scaling.get(key), name=f"scaling.{key}")
            if value <= 0:
                raise ValueError(f"scaling.{key} must be positive")

    return {
        "source_revision": source_revision,
        "target_fingerprint": target_fingerprint,
        "python_version": runtime["python_version"],
        "platform": runtime["platform"],
        "run_count": len(runs),
        "sizes": sizes,
        "scaling_intervals": len(comparisons),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    summary = validate_evidence(args.path)
    print(
        "External Spark evidence provenance verified: "
        f"revision={summary['source_revision']}, target={summary['target_fingerprint']}, "
        f"runs={summary['run_count']}, sizes={summary['sizes']}, "
        f"scaling_intervals={summary['scaling_intervals']}"
    )


if __name__ == "__main__":
    main()
