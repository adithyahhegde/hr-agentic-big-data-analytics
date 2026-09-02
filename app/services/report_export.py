"""Deterministic report assembly without exposing source HR records."""
from __future__ import annotations

import html
import json
from typing import Any


def build_report(dataset_id: str, fingerprint: str, schema_version: str, analytics: dict[str, Any], runs: list[dict[str, Any]], insights: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "report_version": "1.0",
        "dataset_id": dataset_id,
        "dataset_fingerprint": fingerprint,
        "schema_version": schema_version,
        "analytics": analytics,
        "ml_runs": runs,
        "insights": insights or {},
        "privacy": {"raw_records_included": False, "employee_level_identifiers_included": False},
    }


def to_html(report: dict[str, Any]) -> str:
    def block(title: str, value: Any) -> str:
        payload = html.escape(json.dumps(value, indent=2, default=str))
        return f"<section><h2>{html.escape(title)}</h2><pre>{payload}</pre></section>"
    return "<!doctype html><html><head><meta charset='utf-8'><title>HR Analytics Report</title><style>body{font-family:system-ui,sans-serif;max-width:1100px;margin:40px auto;padding:0 20px;color:#172033}section{margin:24px 0}pre{background:#f5f7fa;border:1px solid #dfe4ea;border-radius:8px;padding:16px;overflow:auto}h1{margin-bottom:4px}.meta{color:#596579}</style></head><body>" + f"<h1>HR Analytics Report</h1><p class='meta'>Dataset {html.escape(str(report['dataset_id']))} · fingerprint {html.escape(str(report['dataset_fingerprint']))} · schema {html.escape(str(report['schema_version']))}</p>" + block("Descriptive analytics", report["analytics"]) + block("ML runs", report["ml_runs"]) + block("Evidence-backed insights", report["insights"]) + block("Privacy and provenance", report["privacy"]) + "</body></html>"
