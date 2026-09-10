"""Bounded decision-support synthesis over verified analytical outputs."""
from __future__ import annotations

from typing import Any


_SUPPORTED_OBJECTIVES = {
    "attrition_classification",
    "salary_regression",
    "employee_clustering",
    "anomaly_detection",
}
_MAX_EVIDENCE_ITEMS = 50
_MAX_TEXT_LENGTH = 500


def _text(value: Any, default: str) -> str:
    text = str(value if value is not None else default).strip()
    return text[:_MAX_TEXT_LENGTH]


def _same_dataset(analytics: dict[str, Any], result: dict[str, Any]) -> bool:
    analytics_fingerprint = analytics.get("dataset_fingerprint")
    result_fingerprint = result.get("dataset_fingerprint")
    if analytics_fingerprint:
        if result_fingerprint:
            return result_fingerprint == analytics_fingerprint
        provenance = result.get("provenance")
        if isinstance(provenance, dict):
            return provenance.get("dataset_fingerprint") == analytics_fingerprint
        return False
    return True


def _add_evidence(evidence: list[dict[str, Any]], item: dict[str, Any]) -> str:
    evidence_id = f"evidence-{len(evidence) + 1}"
    evidence.append({"evidence_id": evidence_id, **item})
    return evidence_id


def synthesize(analytics: dict[str, Any], ml_runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Synthesize only bounded, supported evidence tied to the current dataset."""
    evidence: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    rejected_runs = 0

    for item in analytics.get("insights", []):
        if len(evidence) >= _MAX_EVIDENCE_ITEMS:
            break
        evidence_id = _add_evidence(evidence, {
            "source": "descriptive_analytics",
            "type": _text(item.get("type"), "SYSTEM"),
            "severity": _text(item.get("severity"), "INFO"),
            "title": _text(item.get("title"), "Finding"),
            "evidence": _text(item.get("evidence"), ""),
        })
        if item.get("type") == "DATA_QUALITY" and item.get("severity") == "WARNING":
            actions.append({"priority": "HIGH", "action": "Review the affected field and correct or document the underlying data-quality issue before using it for downstream decisions.", "basis": _text(item.get("title"), "Data-quality warning"), "evidence_ids": [evidence_id], "constraint": "This is a data remediation action, not an employee-level decision."})

    for result in ml_runs:
        if len(evidence) >= _MAX_EVIDENCE_ITEMS:
            break
        objective = result.get("objective", "")
        if objective not in _SUPPORTED_OBJECTIVES or not _same_dataset(analytics, result):
            rejected_runs += 1
            continue
        if objective == "employee_clustering":
            k = result.get("selected_k", "multiple")
            silhouette = next((c.get("silhouette") for c in result.get("candidates", []) if c.get("k") == k), None)
            evidence_id = _add_evidence(evidence, {"source": "clustering", "type": "SEGMENTATION", "severity": "INFO", "title": f"{k} workforce segments identified", "evidence": f"K-Means selected {k} segments using silhouette evidence; usable rows: {result.get('rows_used', 0):,}; selected silhouette: {silhouette}."})
            actions.append({"priority": "MEDIUM", "action": "Use aggregate segment profiles to investigate materially different workforce patterns with HR domain owners, then validate whether the segments are operationally meaningful.", "basis": f"The clustering run selected {k} segments using internal separation evidence.", "evidence_ids": [evidence_id], "constraint": "Segments are statistical groupings, not employee labels, risk scores, or employment decisions."})
            continue
        if objective == "anomaly_detection":
            try:
                share = float(result.get("anomaly_share", 0))
            except (TypeError, ValueError):
                rejected_runs += 1
                continue
            if not 0 <= share <= 1:
                rejected_runs += 1
                continue
            evidence_id = _add_evidence(evidence, {"source": "anomaly_detection", "type": "ANOMALY", "severity": "INFO", "title": f"{share * 100:.1f}% of usable rows flagged for review", "evidence": f"{_text(result.get('method'), 'Anomaly detection')} identified multivariate outlier patterns across confirmed predictors; usable rows: {result.get('rows_used', 0):,}."})
            actions.append({"priority": "MEDIUM", "action": "Review the aggregate anomaly pattern for data-quality, process, or population-shift explanations before interpreting it as a workforce signal.", "basis": f"{share * 100:.1f}% of usable rows were flagged by the unsupervised detector.", "evidence_ids": [evidence_id], "constraint": "Anomaly status is a statistical review signal and is not evidence of misconduct, poor performance, or individual risk."})
            continue

        selected = _text(result.get("selected_model"), "model")
        metric = _text(result.get("selection_metric"), "evaluation metric")
        if result.get("execution_mode") == "BOUNDED_AUTOML":
            estimators = ", ".join(_text(item, "learner") for item in result.get("search", {}).get("estimators", []))
            evidence_id = _add_evidence(evidence, {"source": "automl_search", "type": "PREDICTIVE", "severity": "INFO", "title": f"{selected.replace('_', ' ')} selected by bounded AutoML", "evidence": f"FLAML searched the configured learner set ({estimators}) within a {result.get('search', {}).get('time_budget_seconds', 'bounded')} second budget and evaluated the selected model on {result.get('test_rows', 0):,} held-out rows using {metric}."})
            actions.append({"priority": "MEDIUM", "action": "Use the selected model as a predictive investigation aid, inspect its validation metrics and stability, and confirm the underlying business question with domain owners before acting.", "basis": f"Bounded AutoML selected {selected.replace('_', ' ')} using held-out {metric} evidence.", "evidence_ids": [evidence_id], "constraint": "Automated model selection does not establish causality or justify an individual employment decision."})
            continue

        evidence_id = _add_evidence(evidence, {"source": "model_evaluation", "type": "PREDICTIVE", "severity": "INFO", "title": f"{selected.replace('_', ' ')} selected", "evidence": f"Selected from {len(result.get('models', []))} candidates using held-out {metric} evidence; test rows: {result.get('test_rows', 0):,}."})
        top = (result.get("explainability") or {}).get("top_features", [])
        if top:
            names = ", ".join(_text(item.get("feature"), "feature") for item in top[:3])
            actions.append({"priority": "MEDIUM", "action": "Use the strongest model features as candidates for further workforce investigation, then validate them with domain owners and causal analysis before acting.", "basis": f"Top model evidence features: {names}.", "evidence_ids": [evidence_id], "constraint": "Feature importance is associative/predictive evidence and does not establish causality."})

    if not evidence:
        actions.append({"priority": "LOW", "action": "Collect additional validated evidence before making an analytical recommendation.", "basis": "No material evidence was returned by the current analytical tools.", "evidence_ids": [], "constraint": "No automated recommendation should be inferred from an empty result."})

    limitations = [
        "Predictions and unsupervised signals are analytical evidence, not causal conclusions.",
        "Recommendations require human review and should not be used as automated hiring, firing, promotion, or compensation decisions.",
        "Categorical predictors are encoded for local supervised modelling; encoded feature importance may refer to individual category levels rather than the original business field.",
        "Unsupervised clustering and anomaly detection identify statistical patterns that require domain validation and may be sensitive to feature selection and scaling.",
        "Bounded AutoML searches only the configured learner set and time budget; it is not a guarantee of a globally optimal model.",
    ]
    if rejected_runs:
        limitations.append(f"{rejected_runs} analytical run(s) were excluded because their objective, provenance, or values could not be safely verified for the current dataset.")
    return {"agent": "bounded_evidence_synthesizer_v4", "plan": ["collect verified findings", "validate supported objectives and dataset provenance", "classify evidence by analytical source", "rank material signals", "draft reversible investigation actions", "attach evidence-object citations and limitations"], "evidence": evidence, "recommendations": actions, "limitations": limitations, "raw_hr_records_accessed": False}
