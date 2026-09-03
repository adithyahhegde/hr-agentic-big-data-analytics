"""SQLite-backed run ledger for reproducibility, lineage, and failure history."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RunHistory:
    def __init__(self, path: Path | str = "hr_analytics_history.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, dataset_id TEXT NOT NULL, fingerprint TEXT NOT NULL, operation TEXT NOT NULL, engine TEXT, status TEXT NOT NULL, created_at TEXT NOT NULL, result_json TEXT NOT NULL)")
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
        return self.record(dataset_id, fingerprint, operation, "FAILED", {"error_type": type(error).__name__, "message": str(error), "recoverable": isinstance(error, (ValueError, RuntimeError))}, engine)

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
        query += " ORDER BY id DESC LIMIT 1"
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute(query, params).fetchone()
        if not row:
            return None
        result = dict(row)
        try:
            result["result"] = json.loads(result.pop("result_json"))
        except (TypeError, json.JSONDecodeError):
            result["result"] = {}
        return result


history = RunHistory()
