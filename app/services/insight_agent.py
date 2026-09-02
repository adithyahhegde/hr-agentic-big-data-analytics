"""Bounded decision-support synthesis over verified analytical outputs."""
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
        objective = result.get("objective", "")
        if objective == "employee_clustering":
            k = result.get("selected_k", "multiple")
            silhouette = next((c.get("silhouette") for c in result.get("candidates", []) if c.get("k") == k), None)
            evidence.append({"source": "clustering", "type": "SEGMENTATION", "severity": "INFO", "title": f"{k} workforce segments identified", "evidence": f"K-Means selected {k} segments using silhouette evidence; usable rows: {result.get('rows_used', 0):,}; selected silhouette: {silhouette}."})
            actions.append({"priority": "MEDIUM", "action": "Use aggregate segment profiles to investigate materially different workforce patterns with HR domain owners, then validate whether the segments are operationally meaningful.", "basis": f"The clustering run selected {k} segments using internal separation evidence.", "constraint": "Segments are statistical groupings, not employee labels, risk scores, or employment decisions."})
            continue
        if objective == "anomaly_detection":
            share = float(result.get("anomaly_share", 0))
            evidence.append({"source": "anomaly_detection", "type": "ANOMALY", "severity": "INFO", "title": f"{share * 100:.1f}% of usable rows flagged for review", "evidence": f"{result.get('method', 'Anomaly detection')} identified multivariate outlier patterns across confirmed predictors; usable rows: {result.get('rows_used', 0):,}."})
            actions.append({"priority": "MEDIUM", "action": "Review the aggregate anomaly pattern for data-quality, process, or population-shift explanations before interpreting it as a workforce signal.", "basis": f"{share * 100:.1f}% of usable rows were flagged by the unsupervised detector.", "constraint": "Anomaly status is a statistical review signal and is not evidence of misconduct, poor performance, or individual risk."})
            continue
        selected = result.get("selected_model", "model")
        metric = result.get("selection_metric", "evaluation metric")
        evidence.append({"source": "model_evaluation", "type": "PREDICTIVE", "severity": "INFO", "title": f"{selected.replace('_', ' ')} selected", "evidence": f"Selected from {len(result.get('models', []))} candidates using held-out {metric} evidence; test rows: {result.get('test_rows', 0):,}."})
        top = (result.get("explainability") or {}).get("top_features", [])
        if top:
            names = ", ".join(str(item.get("feature")) for item in top[:3])
            actions.append({"priority": "MEDIUM", "action": "Use the strongest model features as candidates for further workforce investigation, then validate them with domain owners and causal analysis before acting.", "basis": f"Top model evidence features: {names}.", "constraint": "Feature importance is associative/predictive evidence and does not establish causality."})

    if not evidence:
        actions.append({"priority": "LOW", "action": "Collect additional validated evidence before making an analytical recommendation.", "basis": "No material evidence was returned by the current analytical tools.", "constraint": "No automated recommendation should be inferred from an empty result."})

    limitations = [
        "Predictions and unsupervised signals are analytical evidence, not causal conclusions.",
        "Recommendations require human review and should not be used as automated hiring, firing, promotion, or compensation decisions.",
        "Categorical predictors are encoded for local supervised modelling; encoded feature importance may refer to individual category levels rather than the original business field.",
        "Unsupervised clustering and anomaly detection identify statistical patterns that require domain validation and may be sensitive to feature selection and scaling.",
    ]
    return {"agent": "bounded_evidence_synthesizer_v2", "plan": ["collect verified findings", "classify evidence by analytical source", "rank material signals", "draft reversible investigation actions", "attach limitations"], "evidence": evidence, "recommendations": actions, "limitations": limitations, "raw_hr_records_accessed": False}
