"""Evaluate bounded planner -> synthesis reliability on deterministic scenarios.

This is a service-level reliability protocol: it exercises the actual planning
and evidence-synthesis contracts together while injecting malformed, unsupported,
and cross-dataset analytical outputs. It intentionally does not claim to measure
LLM quality, human-analyst agreement, or real-world HR generalization.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.insight_agent import synthesize
from app.services.planning_agent import plan_analyses
from app.services.task_detection import TaskCandidate


def _tasks(*objectives: str, row_count: int = 100) -> list[TaskCandidate]:
    features = ("age", "department")
    target = {"attrition_classification": "attrition", "salary_regression": "salary"}
    return [TaskCandidate(objective, "FEASIBLE", target.get(objective), features, ("fixture capability",)) for objective in objectives]


def _scenario(name: str) -> tuple[list[TaskCandidate], dict[str, Any], list[dict[str, Any]], bool]:
    base = {
        "dataset_fingerprint": "fixture-dataset-1",
        "insights": [{"type": "DATA_QUALITY", "severity": "WARNING", "title": "Missing values", "evidence": "Some confirmed fields contain missing values."}],
    }
    valid_ml = {"objective": "attrition_classification", "dataset_fingerprint": "fixture-dataset-1", "selected_model": "logistic_regression", "selection_metric": "f1", "models": [{"name": "logistic_regression"}], "test_rows": 30}
    if name == "valid":
        return _tasks("attrition_classification"), base, [valid_ml], True
    if name == "blocked":
        return [], {"dataset_fingerprint": "fixture-dataset-1", "insights": []}, [], True
    if name == "unsupported_objective":
        return _tasks("attrition_classification"), base, [{**valid_ml, "objective": "arbitrary_employee_decision"}], True
    if name == "cross_dataset":
        return _tasks("attrition_classification"), base, [{**valid_ml, "dataset_fingerprint": "other-dataset"}], True
    if name == "invalid_anomaly_share":
        return _tasks("employee_clustering"), base, [{"objective": "anomaly_detection", "dataset_fingerprint": "fixture-dataset-1", "anomaly_share": 2.0, "method": "isolation_forest", "rows_used": 100}], True
    if name == "malformed_anomaly_share":
        return _tasks("employee_clustering"), base, [{"objective": "anomaly_detection", "dataset_fingerprint": "fixture-dataset-1", "anomaly_share": "not-a-number", "method": "isolation_forest", "rows_used": 100}], True
    if name == "evidence_overflow":
        analytics = {"dataset_fingerprint": "fixture-dataset-1", "insights": [{"type": "DATA_QUALITY", "severity": "WARNING", "title": f"Finding {i}", "evidence": "x" * 1000} for i in range(75)]}
        return _tasks("attrition_classification"), analytics, [], True
    raise ValueError(f"unknown scenario: {name}")


def evaluate(seed: int = 42) -> dict[str, Any]:
    del seed  # Inputs are deterministic; retained for a stable CLI contract.
    names = ("valid", "blocked", "unsupported_objective", "cross_dataset", "invalid_anomaly_share", "malformed_anomaly_share", "evidence_overflow")
    records: list[dict[str, Any]] = []
    settings = Settings(allow_local_llm=False)
    for name in names:
        tasks, analytics, ml_runs, expected_safe = _scenario(name)
        plan = plan_analyses(tasks, settings)
        synthesis = synthesize(analytics, ml_runs)
        evidence_ids = {item["evidence_id"] for item in synthesis["evidence"]}
        cited_ids = {citation for rec in synthesis["recommendations"] for citation in rec.get("evidence_ids", [])}
        citation_integrity = cited_ids <= evidence_ids
        bounded = len(synthesis["evidence"]) <= 50 and all(len(str(item.get("evidence", ""))) <= 500 for item in synthesis["evidence"])
        record = {
            "scenario": name,
            "plan_mode": plan["mode"],
            "plan_count": len(plan["plans"]),
            "evidence_count": len(synthesis["evidence"]),
            "recommendation_count": len(synthesis["recommendations"]),
            "citation_integrity": citation_integrity,
            "bounded_evidence": bounded,
            "rejected_runs_reported": any("excluded" in limitation for limitation in synthesis["limitations"]),
            "safe": citation_integrity and bounded and expected_safe,
        }
        records.append(record)
    passed = sum(record["safe"] for record in records)
    return {"protocol": "bounded_agent_reliability_v1", "seed": 42, "scenarios": list(names), "records": records, "aggregate": {"scenario_count": len(records), "safe_scenarios": passed, "safety_rate": round(passed / len(records), 4)}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.seed)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
