"""Validate externally produced Spark scalability evidence against the frozen protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from pathlib import Path


EXPECTED_PROTOCOL = "external_spark_scalability_v2"
EXPECTED_SEED = 42
EXPECTED_MASTER_KIND = "spark"
EXPECTED_INPUT_MODE = "driver_parallelized_csv"
SOURCE_REVISION_RE = re.compile(r"[0-9a-f]{40}")
HEX_SHA256_RE = re.compile(r"[0-9a-f]{64}")
SPARK_VERSION_RE = re.compile(r"\d+\.\d+\.\d+(?:[-+._][0-9A-Za-z.-]+)?")


def _finite_number(value, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
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
    expected_revision = os.getenv("GITHUB_SHA", "").strip()
    if expected_revision and source_revision != expected_revision:
        raise ValueError("evidence source_revision does not match GITHUB_SHA")

    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        raise ValueError("evidence runtime provenance is required")
    for key in ("python_version", "platform"):
        if not isinstance(runtime.get(key), str) or not runtime[key].strip():
            raise ValueError(f"evidence runtime.{key} is required")

    master_kind = data.get("master_kind")
    if master_kind != EXPECTED_MASTER_KIND:
        raise ValueError(f"evidence master_kind must be {EXPECTED_MASTER_KIND}")

    target_fingerprint = data.get("target_fingerprint")
    if not isinstance(target_fingerprint, str) or not HEX_SHA256_RE.fullmatch(target_fingerprint):
        raise ValueError("evidence target_fingerprint must be a 64-character lowercase SHA-256")
    configured_master = os.getenv("HR_ANALYTICS_SPARK_MASTER", "").strip()
    if configured_master:
        expected_target_fingerprint = hashlib.sha256(configured_master.encode("utf-8")).hexdigest()
        if target_fingerprint != expected_target_fingerprint:
            raise ValueError("evidence target_fingerprint does not match HR_ANALYTICS_SPARK_MASTER")

    expected_spark_version = os.environ.get("SPARK_VALIDATION_VERSION")
    if expected_spark_version is not None:
        expected_spark_version = expected_spark_version.strip()
        if not expected_spark_version or not SPARK_VERSION_RE.fullmatch(expected_spark_version):
            raise ValueError("SPARK_VALIDATION_VERSION must be a valid Spark version string")

    runs = data.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("evidence must contain at least one run")
    if [run.get("rows") for run in runs] != sizes:
        raise ValueError("evidence run row counts must exactly match sizes")

    spark_versions: list[str] = []
    application_ids: list[str] = []
    for run in runs:
        fingerprint = run.get("fixture_sha256")
        if not isinstance(fingerprint, str) or not HEX_SHA256_RE.fullmatch(fingerprint):
            raise ValueError("each evidence run requires a 64-character lowercase fixture_sha256")
        if not isinstance(run.get("fixture_schema"), list) or not run["fixture_schema"]:
            raise ValueError("each evidence run requires a non-empty fixture_schema")
        if not isinstance(run.get("rows"), int) or isinstance(run.get("rows"), bool) or run["rows"] <= 0:
            raise ValueError("each evidence run requires positive rows")
        elapsed = _finite_number(run.get("elapsed_seconds"), name="elapsed_seconds")
        throughput = _finite_number(run.get("rows_per_second"), name="rows_per_second")
        if elapsed <= 0:
            raise ValueError("each evidence run requires positive elapsed_seconds")
        if throughput <= 0:
            raise ValueError("each evidence run requires positive rows_per_second")

        validation = run.get("validation")
        if not isinstance(validation, dict):
            raise ValueError("each evidence run requires validation metadata")
        for key in ("row_count_matches_fixture", "distributed", "raw_rows_returned", "aggregates_match_local_baseline", "spark_version_present", "parallelism_positive", "application_id_present"):
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
        spark_version = execution.get("spark_version")
        if not isinstance(spark_version, str) or not spark_version.strip():
            raise ValueError("each evidence run requires execution.spark_version")
        if expected_spark_version is not None and spark_version != expected_spark_version:
            raise ValueError("evidence Spark version does not match SPARK_VALIDATION_VERSION")
        parallelism = execution.get("default_parallelism")
        if not isinstance(parallelism, int) or isinstance(parallelism, bool) or parallelism <= 0:
            raise ValueError("each evidence run requires positive execution.default_parallelism")
        application_id = execution.get("application_id")
        if not isinstance(application_id, str) or not application_id.strip():
            raise ValueError("each evidence run requires execution.application_id")
        if execution.get("input_mode") != EXPECTED_INPUT_MODE:
            raise ValueError(f"evidence input_mode must be {EXPECTED_INPUT_MODE}")
        spark_versions.append(spark_version)
        application_ids.append(application_id)

    if len(set(spark_versions)) != 1:
        raise ValueError("all evidence runs must use the same Spark version")
    if len(set(application_ids)) != len(application_ids):
        raise ValueError("evidence application IDs must be unique per benchmark run")

    scaling = data.get("scaling")
    if not isinstance(scaling, dict):
        raise ValueError("evidence scaling summary is required")
    comparisons = scaling.get("adjacent_comparisons")
    if not isinstance(comparisons, list) or len(comparisons) != max(0, len(runs) - 1):
        raise ValueError("evidence scaling adjacent_comparisons must match the number of benchmark intervals")
    for index, comparison in enumerate(comparisons):
        if not isinstance(comparison, dict):
            raise ValueError("each evidence scaling comparison must be an object")
        if comparison.get("from_rows") != runs[index]["rows"] or comparison.get("to_rows") != runs[index + 1]["rows"]:
            raise ValueError("evidence scaling comparison row bounds do not match benchmark runs")
        row_growth = _finite_number(comparison.get("row_growth_factor"), name="scaling.row_growth_factor")
        elapsed_growth = _finite_number(comparison.get("elapsed_growth_factor"), name="scaling.elapsed_growth_factor")
        throughput_growth = _finite_number(comparison.get("throughput_growth_factor"), name="scaling.throughput_growth_factor")
        if row_growth <= 0:
            raise ValueError("scaling.row_growth_factor must be positive")
        if elapsed_growth <= 0:
            raise ValueError("scaling.elapsed_growth_factor must be positive")
        if throughput_growth <= 0:
            raise ValueError("scaling.throughput_growth_factor must be positive")
        expected_row_growth = runs[index + 1]["rows"] / runs[index]["rows"]
        expected_elapsed_growth = runs[index + 1]["elapsed_seconds"] / runs[index]["elapsed_seconds"]
        expected_throughput_growth = runs[index + 1]["rows_per_second"] / runs[index]["rows_per_second"]
        if not math.isclose(row_growth, expected_row_growth, rel_tol=1e-6, abs_tol=1e-9):
            raise ValueError("scaling.row_growth_factor does not match benchmark runs")
        if not math.isclose(elapsed_growth, expected_elapsed_growth, rel_tol=1e-6, abs_tol=1e-9):
            raise ValueError("scaling.elapsed_growth_factor does not match benchmark runs")
        if not math.isclose(throughput_growth, expected_throughput_growth, rel_tol=1e-6, abs_tol=1e-9):
            raise ValueError("scaling.throughput_growth_factor does not match benchmark runs")
    if len(runs) >= 2:
        expected_ratios = {
            "largest_to_smallest_elapsed_ratio": runs[-1]["elapsed_seconds"] / runs[0]["elapsed_seconds"],
            "largest_to_smallest_throughput_ratio": runs[-1]["rows_per_second"] / runs[0]["rows_per_second"],
        }
        for key, expected in expected_ratios.items():
            actual = _finite_number(scaling.get(key), name=f"scaling.{key}")
            if actual <= 0:
                raise ValueError(f"scaling.{key} must be positive")
            if not math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-9):
                raise ValueError(f"scaling.{key} does not match benchmark runs")

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
