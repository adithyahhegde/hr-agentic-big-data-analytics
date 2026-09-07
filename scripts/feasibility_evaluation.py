"""Reproducible objective-feasibility evaluation for the HR analytics task detector."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.task_detection import IDENTIFIER_FIELDS, detect_tasks

OBJECTIVES = ("attrition_classification", "salary_regression", "employee_clustering", "anomaly_detection")
MAPPINGS = {
    "employee_id": "employee_id", "age": "age", "department": "department",
    "salary": "salary", "performance_rating": "performance_rating", "bonus": "bonus", "attrition": "attrition",
}
SCENARIOS = {
    "clean": MAPPINGS,
    "messy": {"Employee ID": "employee_id", "Employee Age": "age", "Dept": "department", "Annual Pay": "salary", "Performance": "performance_rating", "Bonus Pay": "bonus", "Left Company": "attrition"},
    "categorical": {"Employee ID": "employee_id", "Department": "department", "Performance": "performance_rating", "Attrition": "attrition"},
    "mixed": MAPPINGS,
    "ambiguous": {"Employee ID": "employee_id", "Worker ID": "employee_id", "Age": "age", "Department": "department", "Salary": "salary", "Attrition": "attrition"},
    "leakage_prone": {**MAPPINGS, "Salary Copy": "salary", "Attrition Copy": "attrition"},
}
BLOCKED_SCENARIOS = {"ambiguous", "leakage_prone"}


def expected(rows: int, scenario: str) -> dict[str, bool]:
    if rows < 20 or scenario in BLOCKED_SCENARIOS:
        return {objective: False for objective in OBJECTIVES}
    if scenario == "categorical":
        return {"attrition_classification": True, "salary_regression": False, "employee_clustering": True, "anomaly_detection": True}
    return {objective: True for objective in OBJECTIVES}


def baseline(rows: int, scenario: str) -> dict[str, bool]:
    """Weak baseline that ignores predictor sufficiency and schema collisions."""
    if rows < 20:
        return {objective: False for objective in OBJECTIVES}
    canonical = set(SCENARIOS[scenario].values()) - IDENTIFIER_FIELDS - {"unknown"}
    return {
        "attrition_classification": "attrition" in canonical,
        "salary_regression": "salary" in canonical,
        "employee_clustering": len(canonical - {"salary", "attrition"}) >= 2,
        "anomaly_detection": len(canonical - {"salary", "attrition"}) >= 2,
    }


def evaluate(sizes: tuple[int, ...] = (10, 20, 100), seed: int = 42) -> dict[str, Any]:
    if not sizes or any(size < 1 for size in sizes):
        raise ValueError("sizes must contain only positive values")
    records = []
    for rows in sizes:
        for scenario, mappings in SCENARIOS.items():
            observed = {objective: False for objective in OBJECTIVES}
            if scenario not in BLOCKED_SCENARIOS:
                observed = {task.objective: task.status == "FEASIBLE" for task in detect_tasks(mappings, rows)}
            exp = expected(rows, scenario)
            base = baseline(rows, scenario)
            records.append({"rows": rows, "scenario": scenario, "expected": exp, "pipeline": observed, "baseline": base})
    total = len(records) * len(OBJECTIVES)
    pipeline_correct = sum(r["pipeline"][o] == r["expected"][o] for r in records for o in OBJECTIVES)
    baseline_correct = sum(r["baseline"][o] == r["expected"][o] for r in records for o in OBJECTIVES)
    return {"seed": seed, "sizes": list(sizes), "objectives": list(OBJECTIVES), "records": records,
            "accuracy": {"pipeline": round(pipeline_correct / total, 4), "baseline": round(baseline_correct / total, 4)}}


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[10, 20, 100])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(tuple(args.sizes), args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
