"""SQLite-backed run ledger for reproducibility, lineage, and failure history."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RunHistory:
    def __init__(self, path: Path | str = "data/hr_analytics.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, dataset_id TEXT NOT NULL, fingerprint TEXT NOT NULL, operation TEXT NOT NULL, engine TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL, result_json TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS explanation_artifacts (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL UNIQUE, dataset_id TEXT NOT NULL, fingerprint TEXT NOT NULL, schema_version TEXT, operation TEXT NOT NULL, created_at TEXT NOT NULL, artifact_json TEXT NOT NULL)")
            db.commit()

    def record(self, dataset_id: str, fingerprint: str, operation: str, status: str, result: dict[str, Any], engine: str | None = None) -> int:
        safe_result = dict(result)
        safe_result.setdefault("provenance", {})
        safe_result["provenance"].update({"dataset_id": dataset_id, "dataset_fingerprint": fingerprint, "operation": operation, "engine": engine, "recorded_at": datetime.now(timezone.utc).isoformat()})
        with sqlite3.connect(self.path) as db:
            cursor = db.execute("INSERT INTO runs(dataset_id,fingerprint,operation,engine,status,created_at,result_json) VALUES(?,?,?,?,?,?,?)", (dataset_id, fingerprint, operation, engine, status, datetime.now(timezone.utc).isoformat(), json.dumps(safe_result, default=str)))
            db.commit()
            return int(cursor.lastrowid)

    def record_failure(self, dataset_id: str, fingerprint: str, operation: str, error: Exception, engine: str | None = None) -> int:
        return self.record_failure_safe(dataset_id, fingerprint, operation, type(error).__name__, engine)

    def record_failure_safe(self, dataset_id: str, fingerprint: str, operation: str, error_type: str, engine: str | None = None) -> int:
        safe_type = str(error_type).split(".")[-1][:100] or "Exception"
        return self.record(dataset_id, fingerprint, operation, "FAILED", {"error_type": safe_type, "message": "Execution failed; inspect server logs for diagnostic details.", "recoverable": safe_type in {"ValueError", "RuntimeError"}}, engine)

    def record_explanation(self, run_id: int, dataset_id: str, fingerprint: str, operation: str, explanation: dict[str, Any], schema_version: str | None = None) -> int:
        """Persist a bounded, non-row-level explanation artifact for a successful run."""
        method = str(explanation.get("method", "unspecified"))[:120]
        raw_features = explanation.get("top_features", [])
        features: list[dict[str, Any]] = []
        if isinstance(raw_features, list):
            for item in raw_features[:10]:
                if not isinstance(item, dict):
                    continue
                feature = str(item.get("feature", ""))[:200]
                if not feature:
                    continue
                safe_item = {"feature": feature}
                if "importance" in item:
                    try:
                        safe_item["importance"] = round(float(item["importance"]), 6)
                    except (TypeError, ValueError):
                        continue
                features.append(safe_item)
        artifact = {"method": method, "top_features": features, "limitations": [str(value)[:300] for value in explanation.get("limitations", [])[:5]] if isinstance(explanation.get("limitations"), list) else []}
        created_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.path) as db:
            cursor = db.execute("INSERT OR REPLACE INTO explanation_artifacts(run_id,dataset_id,fingerprint,schema_version,operation,created_at,artifact_json) VALUES(?,?,?,?,?,?,?)", (run_id, dataset_id, fingerprint, schema_version, operation, created_at, json.dumps(artifact, default=str)))
            db.commit()
            return int(cursor.lastrowid)

    def latest_explanation(self, dataset_id: str, operation: str | None = None, fingerprint: str | None = None, schema_version: str | None = None) -> dict[str, Any] | None:
        """Return the newest explanation artifact matching the current dataset lineage."""
        query = "SELECT * FROM explanation_artifacts WHERE dataset_id=?"
        params: list[Any] = [dataset_id]
        if operation:
            query += " AND operation=?"
            params.append(operation)
        if fingerprint:
            query += " AND fingerprint=?"
            params.append(fingerprint)
        if schema_version is not None:
            query += " AND schema_version=?"
            params.append(schema_version)
        query += " ORDER BY id DESC LIMIT 1"
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(query, params).fetchone()
        if not row:
            return None
        try:
            artifact = json.loads(row["artifact_json"])
        except (TypeError, json.JSONDecodeError):
            return None
        if not isinstance(artifact, dict):
            return None
        artifact["artifact_id"] = int(row["id"])
        artifact["run_id"] = int(row["run_id"])
        artifact["dataset_id"] = row["dataset_id"]
        artifact["dataset_fingerprint"] = row["fingerprint"]
        artifact["schema_version"] = row["schema_version"]
        artifact["operation"] = row["operation"]
        artifact["created_at"] = row["created_at"]
        return artifact

    def list(self, dataset_id: str, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT id,dataset_id,fingerprint,operation,engine,status,created_at FROM runs WHERE dataset_id=? ORDER BY id DESC LIMIT ?", (dataset_id, limit)).fetchall()
        return [dict(row) for row in rows]

    def latest(self, dataset_id: str, operation: str | None = None) -> dict[str, Any] | None:
        query = "SELECT * FROM runs WHERE dataset_id=?"
        params: list[Any] = [dataset_id]
        if operation:
            query += " AND operation=?"
            params.append(operation)
        query += " AND status='SUCCEEDED' ORDER BY id DESC LIMIT 1"
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(query, params).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["result_json"])
        except (TypeError, json.JSONDecodeError):
            return None

    def latest_matching(self, dataset_id: str, operation: str, fingerprint: str, schema_version: str | None = None) -> dict[str, Any] | None:
        """Return the newest valid successful run for a dataset fingerprint.

        Avoid SQLite JSON-extension functions so the recovery path works with
        minimal SQLite builds. Schema matching is validated after decoding the
        bounded result payload, while fingerprint matching remains indexed by
        the ledger's ordinary TEXT column.
        """
        query = "SELECT * FROM runs WHERE dataset_id=? AND operation=? AND fingerprint=? AND status='SUCCEEDED' ORDER BY id DESC"
        params: list[Any] = [dataset_id, operation, fingerprint]
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(query, params).fetchall()

        for row in rows:
            try:
                result = json.loads(row["result_json"])
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(result, dict):
                continue
            provenance = result.get("provenance", {})
            if not isinstance(provenance, dict) or provenance.get("dataset_fingerprint") != fingerprint:
                continue
            if schema_version is not None and result.get("schema_version") != schema_version:
                continue
            return result
        return None


history = RunHistory()
