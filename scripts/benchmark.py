"""Benchmark deterministic HR analytics fixtures across representative data sizes and schema conditions."""
from __future__ import annotations

import argparse
import csv
import json
import random
import tempfile
import time
from pathlib import Path
from typing import Any

from app.services.analytics import analyze_csv
from app.services.task_detection import detect_tasks
from app.services.workload_router import WorkloadProfile, route_workload

MAPPINGS = {
    "employee_id": "employee_id",
    "age": "age",
    "department": "department",
    "salary": "salary",
    "performance_rating": "performance_rating",
    "bonus": "bonus",
    "attrition": "attrition",
}

SCHEMA_SCENARIOS = {
    "clean": MAPPINGS,
    "messy": {
        "Employee ID": "employee_id", "Employee Age": "age", "Dept": "department",
        "Annual Pay": "salary", "Performance": "performance_rating", "Bonus Pay": "bonus",
        "Left Company": "attrition",
    },
    "categorical": {
        "Employee ID": "employee_id", "Department": "department", "Performance": "performance_rating",
        "Attrition": "attrition",
    },
    "mixed": MAPPINGS,
}

DEPARTMENTS = ("Engineering", "Sales", "Finance", "HR", "Operations")


def make_fixture(path: Path, rows: int, seed: int) -> None:
    rng = random.Random(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = tuple(MAPPINGS)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for i in range(1, rows + 1):
            age = rng.randint(21, 60)
            salary = rng.randint(35000, 180000)
            performance = rng.randint(1, 5)
            bonus = round(salary * rng.uniform(0.02, 0.18), 2)
            attrition = "Yes" if rng.random() < 0.16 else "No"
            writer.writerow((i, age, rng.choice(DEPARTMENTS), salary, performance, bonus, attrition))


def summarize(result: dict[str, Any], elapsed: float, size_bytes: int) -> dict[str, Any]:
    return {
        "engine": result.get("engine", "LOCAL"), "elapsed_seconds": round(elapsed, 4),
        "rows": result.get("row_count", 0), "bytes": size_bytes,
        "rows_per_second": round(result.get("row_count", 0) / max(elapsed, 1e-9), 2),
        "duplicate_rows": result.get("duplicate_row_count", 0),
        "numeric_fields": len(result.get("numeric_summary", [])),
        "categorical_fields": len(result.get("categorical_summary", [])),
    }


def run(rows: int, seed: int, scenario: str = "clean") -> dict[str, Any]:
    if rows < 1:
        raise ValueError("rows must be positive")
    if scenario not in SCHEMA_SCENARIOS:
        raise ValueError(f"unknown scenario: {scenario}")
    mappings = SCHEMA_SCENARIOS[scenario]
    with tempfile.TemporaryDirectory(prefix="hr_benchmark_") as tmp:
        path = Path(tmp) / "benchmark.csv"
        make_fixture(path, rows, seed)
        size_bytes = path.stat().st_size
        profile = WorkloadProfile(row_count=rows, column_count=len(MAPPINGS), estimated_bytes=size_bytes)
        routed = route_workload(profile)
        start = time.perf_counter()
        local = analyze_csv(path, MAPPINGS)
        local_elapsed = time.perf_counter() - start
        tasks = detect_tasks(mappings, rows)
        output: dict[str, Any] = {
            "fixture": {"rows": rows, "seed": seed, "bytes": size_bytes, "scenario": scenario},
            "routing": {"selected_engine": routed.value},
            "local": summarize(local, local_elapsed, size_bytes),
            "task_detection": {
                "feasible": sorted(task.objective for task in tasks if task.status == "FEASIBLE"),
                "blocked": sorted(task.objective for task in tasks if task.status == "BLOCKED"),
            },
        }
        try:
            from app.services.spark_analytics import analyze_spark
            start = time.perf_counter()
            spark = analyze_spark(path, MAPPINGS)
        except (ImportError, ModuleNotFoundError) as exc:
            output["spark"] = {"available": False, "reason": type(exc).__name__}
            return output
        spark_elapsed = time.perf_counter() - start
        output["spark"] = {"available": True, **summarize(spark, spark_elapsed, size_bytes)}
        output["consistency"] = {
            "row_count_equal": local.get("row_count") == spark.get("row_count"),
            "duplicate_count_equal": local.get("duplicate_row_count") == spark.get("duplicate_row_count"),
        }
        return output


def run_matrix(sizes: tuple[int, ...] = (100, 1000, 10000), seed: int = 42) -> dict[str, Any]:
    """Execute a reproducible size/scenario matrix without exposing employee rows."""
    results = []
    for rows in sizes:
        for scenario in SCHEMA_SCENARIOS:
            result = run(rows, seed, scenario)
            results.append(result)
    return {"seed": seed, "sizes": list(sizes), "scenarios": list(SCHEMA_SCENARIOS), "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenario", choices=tuple(SCHEMA_SCENARIOS), default="clean")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_matrix(seed=args.seed) if args.matrix else run(args.rows, args.seed, args.scenario)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
