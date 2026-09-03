"""Durable dataset manifests and workflow state."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DatasetRegistry:
    def __init__(self, path: Path | str = "data/hr_analytics.sqlite3") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS datasets (
                dataset_id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                row_count INTEGER NOT NULL,
                column_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL,
                profile_json TEXT,
                mappings_json TEXT
            )""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(datasets)").fetchall()}
            if "profile_json" not in columns:
                db.execute("ALTER TABLE datasets ADD COLUMN profile_json TEXT")
            if "mappings_json" not in columns:
                db.execute("ALTER TABLE datasets ADD COLUMN mappings_json TEXT")
            db.commit()

    def register(self, dataset: Any) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("""INSERT OR REPLACE INTO datasets
                (dataset_id,fingerprint,filename,path,size_bytes,row_count,column_count,created_at,status,profile_json,mappings_json)
                VALUES(?,?,?,?,?,?,?,?,?,?,COALESCE((SELECT mappings_json FROM datasets WHERE dataset_id=?),NULL))""", (
                dataset.dataset_id, dataset.sha256, dataset.filename, str(dataset.path),
                dataset.size_bytes, dataset.row_count, dataset.column_count,
                datetime.now(timezone.utc).isoformat(), "STORED", None, dataset.dataset_id,
            ))
            db.commit()

    def save_profile(self, dataset_id: str, profile: Any) -> None:
        payload = profile.model_dump(mode="json")
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE datasets SET profile_json=? WHERE dataset_id=?", (json.dumps(payload), dataset_id))
            db.commit()

    def save_mappings(self, dataset_id: str, mappings: dict[str, str]) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE datasets SET mappings_json=? WHERE dataset_id=?", (json.dumps(mappings), dataset_id))
            db.commit()

    def get_profile(self, dataset_id: str) -> dict[str, Any] | None:
        manifest = self.get(dataset_id)
        if not manifest or not manifest.get("profile_json"):
            return None
        return json.loads(manifest["profile_json"])

    def get_mappings(self, dataset_id: str) -> dict[str, str] | None:
        manifest = self.get(dataset_id)
        if not manifest or not manifest.get("mappings_json"):
            return None
        return json.loads(manifest["mappings_json"])

    def get(self, dataset_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM datasets WHERE dataset_id=?", (dataset_id,)).fetchone()
        return dict(row) if row else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM datasets ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]


registry = DatasetRegistry()
