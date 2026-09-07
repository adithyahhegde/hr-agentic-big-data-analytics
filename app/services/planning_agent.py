"""Bounded analytical planning agent.

The planner reasons only over verified schema/capability metadata. It cannot
invent targets, fields, statistics, or arbitrary tools. When a local LLM is
enabled it may rank the already-validated candidate investigations; otherwise
a deterministic policy produces the same safe plan offline.
"""
from __future__ import annotations

from typing import Any

from app.config import Settings
from app.services.local_llm import LocalLLMError, plan_analytical_objectives
from app.services.task_detection import TaskCandidate


def _candidate(task: TaskCandidate) -> dict[str, Any]:
    labels = {
        "attrition_classification": ("Understand employee attrition", "What workforce characteristics are associated with observed attrition?", "classification"),
        "salary_regression": ("Understand compensation patterns", "How does compensation vary with the confirmed workforce attributes?", "regression"),
        "employee_clustering": ("Discover workforce segments", "Are there materially different aggregate employee profiles?", "segmentation"),
        "anomaly_detection": ("Find unusual workforce patterns", "Are there unusual multivariate workforce profiles that warrant review?", "anomaly screening"),
    }
    title, question, method = labels.get(task.objective, (task.objective.replace("_", " ").title(), "What does this dataset support?", task.objective))
    return {
        "objective": task.objective,
        "title": title,
        "question": question,
        "method": method,
        "target_field": task.target_field,
        "feature_count": len(task.feature_fields),
        "feature_fields": list(task.feature_fields),
        "reasons": list(task.reasons),
        "status": task.status,
    }


def _fallback(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority = {
        "attrition_classification": ("HIGH", 1, ["Validate the outcome distribution", "Compare observed patterns across key workforce dimensions", "Compare suitable classification candidates on held-out evidence", "Inspect predictive signals without treating them as causal"]),
        "salary_regression": ("MEDIUM", 2, ["Inspect compensation distribution", "Compare compensation across confirmed workforce dimensions", "Compare suitable regression candidates on held-out evidence"]),
        "employee_clustering": ("MEDIUM", 3, ["Compare candidate cluster counts", "Profile aggregate segments", "Validate segment usefulness with HR domain owners"]),
        "anomaly_detection": ("LOW", 4, ["Screen for multivariate outlier patterns", "Inspect aggregate anomaly share and score distribution", "Validate data-quality or population explanations"]),
    }
    ordered = sorted(candidates, key=lambda x: priority.get(x["objective"], ("LOW", 99, []))[1])
    plans = []
    for item in ordered:
        level, _, steps = priority.get(item["objective"], ("LOW", 99, ["Collect additional evidence before analysis"]))
        plans.append({**item, "priority": level, "steps": steps, "planning_basis": "deterministic_capability_policy"})
    return plans


def plan_analyses(tasks: list[TaskCandidate], settings: Settings) -> dict[str, Any]:
    """Produce an evidence-bounded analytical plan from feasible capabilities."""
    candidates = [_candidate(task) for task in tasks if task.status == "FEASIBLE"]
    fallback = _fallback(candidates)
    if not candidates:
        return {
            "agent": "bounded_analytical_planner_v1",
            "mode": "deterministic_fallback",
            "objective": None,
            "plans": [],
            "reason": "No feasible analytical objective was established by the confirmed schema and dataset-size gates.",
            "raw_hr_records_accessed": False,
        }

    if not settings.allow_local_llm:
        return {
            "agent": "bounded_analytical_planner_v1",
            "mode": "deterministic_fallback",
            "objective": fallback[0]["objective"],
            "plans": fallback,
            "raw_hr_records_accessed": False,
        }

    try:
        ranked = plan_analytical_objectives(
            candidates=candidates,
            base_url=settings.local_llm_base_url,
            model=settings.local_llm_model,
            timeout_seconds=settings.local_llm_timeout_seconds,
        )
    except LocalLLMError:
        return {
            "agent": "bounded_analytical_planner_v1",
            "mode": "deterministic_fallback",
            "objective": fallback[0]["objective"],
            "plans": fallback,
            "raw_hr_records_accessed": False,
            "fallback_reason": "Local planner unavailable; deterministic plan retained.",
        }

    allowed = {item["objective"] for item in candidates}
    plans = []
    for choice in ranked:
        objective = choice.get("objective")
        if objective not in allowed:
            continue
        base = next(item for item in candidates if item["objective"] == objective)
        plans.append({
            **base,
            "priority": choice.get("priority", "MEDIUM"),
            "steps": choice.get("steps", []),
            "planning_basis": "local_llm_bounded_candidate_ranking",
            "agent_reason": choice.get("reason", "Ranked from validated analytical capabilities."),
        })
    if not plans:
        plans = fallback
        mode = "deterministic_fallback"
    else:
        mode = "local_llm_bounded"
    return {
        "agent": "bounded_analytical_planner_v1",
        "mode": mode,
        "objective": plans[0]["objective"],
        "plans": plans,
        "raw_hr_records_accessed": False,
    }
