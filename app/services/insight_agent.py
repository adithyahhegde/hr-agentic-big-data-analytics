"""Bounded decision-support synthesis over verified analytical outputs.

This layer behaves like a conservative analytical agent: it plans from available
signals, ranks evidence, and emits actions with explicit evidence and limits.
It never reads unrestricted raw HR records and never makes employment decisions.
"""
from __future__ import annotations

from typing import Any


def synthesize(analytics: dict[str, Any], ml_runs: list[dict[str, Any]]) -> dict[str, Any]:
    evidence: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []

    for item in analytics.get("insights", []):
        evidence.append({"source": "descriptive_analytics", "type": item.get("type", "SYSTEM"), "severity": item.get("severity", "INFO"), "title": item.get("title", "Finding"), "evidence": item.get("evidence", "")})
        if item.get("type") == "DATA_QUALITY" and item.get("severity") == "WARNING":
            actions.append({"priority": "HIGH", "action": "Review the affected field and correct or document the underlying data-quality issue before using it for downstream decisions.", "basis": item.get("title", "Data-quality warning"), "constraint": "This is a data remediation action, not an employee-level decision."})

    for result in ml_runs:
        selected = result.get("selected_model", "model")
        metric = result.get("selection_metric", "evaluation metric")
        best = next((m for m in result.get("models", []) if m.get("model") == selected), None)
        evidence.append({"source": "model_evaluation", "type": "PREDICTIVE", "severity": "INFO", "title": f"{selected.replace('_', ' ')} selected", "evidence": f"Selected from {len(result.get('models', []))} candidates using held-out {metric} evidence; test rows: {result.get('test_rows', 0):,}."})
        top = (result.get("explainability") or {}).get("top_features", [])
        if top:
            names = ", ".join(str(item.get("feature")) for item in top[:3])
            actions.append({"priority": "MEDIUM", "action": "Use the strongest model features as candidates for further workforce investigation, then validate them with domain owners and causal analysis before acting.", "basis": f"Top model evidence features: {names}.", "constraint": "Feature importance is associative/predictive evidence and does not establish causality."})

    if not evidence:
        actions.append({"priority": "LOW", "action": "Collect additional validated evidence before making an analytical recommendation.", "basis": "No material evidence was returned by the current analytical tools.", "constraint": "No automated recommendation should be inferred from an empty result."})

    limitations = [
        "Predictions describe model performance on a held-out sample; they do not prove causal relationships.",
        "Recommendations require human review and should not be used as automated hiring, firing, promotion, or compensation decisions.",
        "Current supervised models use confirmed numeric predictors; broader categorical feature preparation is not yet enabled.",
    ]
    return {
        "agent": "bounded_evidence_synthesizer_v1",
        "plan": ["collect verified findings", "rank by severity and predictive evidence", "draft reversible actions", "attach limitations"],
        "evidence": evidence,
        "recommendations": actions,
        "limitations": limitations,
        "raw_hr_records_accessed": False,
    }
