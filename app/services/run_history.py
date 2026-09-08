"""SQLite-backed run ledger with authenticated ownership isolation."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.access_control import current_user


class RunHistory:
    def __init__(self, path: Path | str = "data/hr_analytics.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, dataset_id TEXT NOT NULL, fingerprint TEXT NOT NULL, operation TEXT NOT NULL, engine TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL, result_json TEXT NOT NULL, owner_id TEXT NOT NULL DEFAULT 'local')")
            db.execute("CREATE TABLE IF NOT EXISTS explanation_artifacts (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL UNIQUE, dataset_id TEXT NOT NULL, fingerprint TEXT NOT NULL, schema_version TEXT, operation TEXT NOT NULL, created_at TEXT NOT NULL, artifact_json TEXT NOT NULL, owner_id TEXT NOT NULL DEFAULT 'local')")
            for table, column in (("runs", "owner_id"), ("explanation_artifacts", "owner_id")):
                columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                if column not in columns:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT NOT NULL DEFAULT 'local'")
            db.execute("CREATE INDEX IF NOT EXISTS idx_runs_owner_dataset ON runs(owner_id, dataset_id, id DESC)")
            db.execute("CREATE INDEX IF NOT EXISTS idx_explanations_owner_dataset ON explanation_artifacts(owner_id, dataset_id, id DESC)")
            db.commit()

    @staticmethod
    def _owner() -> str:
        return current_user()

    def record(self, dataset_id: str, fingerprint: str, operation: str, status: str, result: dict[str, Any], engine: str | None = None) -> int:
        safe_result = dict(result)
        safe_result.setdefault("provenance", {})
        safe_result["provenance"].update({"dataset_id": dataset_id, "dataset_fingerprint": fingerprint, "operation": operation, "engine": engine, "recorded_at": datetime.now(timezone.utc).isoformat()})
        owner = self._owner()
        with sqlite3.connect(self.path) as db:
            cursor = db.execute("INSERT INTO runs(dataset_id,fingerprint,operation,engine,status,created_at,result_json,owner_id) VALUES(?,?,?,?,?,?,?,?)", (dataset_id, fingerprint, operation, engine, status, datetime.now(timezone.utc).isoformat(), json.dumps(safe_result, default=str), owner))
            db.commit()
            run_id = int(cursor.lastrowid)
        if status == "SUCCEEDED" and isinstance(result.get("explainability"), dict):
            self.record_explanation(run_id, dataset_id, fingerprint, operation, result["explainability"], result.get("schema_version"))
        return run_id

    def record_failure(self, dataset_id: str, fingerprint: str, operation: str, error: Exception, engine: str | None = None) -> int:
        return self.record_failure_safe(dataset_id, fingerprint, operation, type(error).__name__, engine)

    def record_failure_safe(self, dataset_id: str, fingerprint: str, operation: str, error_type: str, engine: str | None = None) -> int:
        safe_type = str(error_type).split(".")[-1][:100] or "Exception"
        return self.record(dataset_id, fingerprint, operation, "FAILED", {"error_type": safe_type, "message": "Execution failed; inspect server logs for diagnostic details.", "recoverable": safe_type in {"ValueError", "RuntimeError"}}, engine)

    def record_explanation(self, run_id: int, dataset_id: str, fingerprint: str, operation: str, explanation: dict[str, Any], schema_version: str | None = None) -> int:
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
        raw_limitations = explanation.get("limitations", [])
        limitations = [str(value)[:300] for value in raw_limitations[:5]] if isinstance(raw_limitations, list) else []
        artifact = {"method": method, "top_features": features, "limitations": limitations}
        with sqlite3.connect(self.path) as db:
            cursor = db.execute("INSERT OR REPLACE INTO explanation_artifacts(run_id,dataset_id,fingerprint,schema_version,operation,created_at,artifact_json,owner_id) VALUES(?,?,?,?,?,?,?,?)", (run_id, dataset_id, fingerprint, schema_version, operation, datetime.now(timezone.utc).isoformat(), json.dumps(artifact, default=str), self._owner()))
            db.commit()
            return int(cursor.lastrowid)

    def latest_explanation(self, dataset_id: str, operation: str | None = None, fingerprint: str | None = None, schema_version: str | None = None) -> dict[str, Any] | None:
        query = "SELECT * FROM explanation_artifacts WHERE dataset_id=? AND owner_id=?"
        params: list[Any] = [dataset_id, self._owner()]
        if operation:
            query += " AND operation=?"; params.append(operation)
        if fingerprint:
            query += " AND fingerprint=?"; params.append(fingerprint)
        if schema_version is not None:
            query += " AND schema_version=?"; params.append(schema_version)
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
        artifact.update({"artifact_id": int(row["id"]), "run_id": int(row["run_id"]), "dataset_id": row["dataset_id"], "dataset_fingerprint": row["fingerprint"], "schema_version": row["schema_version"], "operation": row["operation"], "created_at": row["created_at"]})
        return artifact

    def list(self, dataset_id: str, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT id,dataset_id,fingerprint,operation,engine,status,created_at FROM runs WHERE dataset_id=? AND owner_id=? ORDER BY id DESC LIMIT ?", (dataset_id, self._owner(), limit)).fetchall()
        return [dict(row) for row in rows]

    def latest(self, dataset_id: str, operation: str | None = None) -> dict[str, Any] | None:
        query = "SELECT * FROM runs WHERE dataset_id=? AND owner_id=?"; params: list[Any] = [dataset_id, self._owner()]
        if operation:
            query += " AND operation=?"; params.append(operation)
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
        query = "SELECT * FROM runs WHERE dataset_id=? AND operation=? AND fingerprint=? AND status='SUCCEEDED' AND owner_id=? ORDER BY id DESC"
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute(query, (dataset_id, operation, fingerprint, self._owner())).fetchall()
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
