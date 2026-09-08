"""Durable dataset manifests and workflow state."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.access_control import current_user


class DatasetAccessError(PermissionError):
    """Raised when a dataset belongs to another request identity."""


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
                mappings_json TEXT,
                owner_id TEXT NOT NULL DEFAULT 'local'
            )""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(datasets)").fetchall()}
            if "profile_json" not in columns:
                db.execute("ALTER TABLE datasets ADD COLUMN profile_json TEXT")
            if "mappings_json" not in columns:
                db.execute("ALTER TABLE datasets ADD COLUMN mappings_json TEXT")
            if "owner_id" not in columns:
                db.execute("ALTER TABLE datasets ADD COLUMN owner_id TEXT NOT NULL DEFAULT 'local'")
            db.execute("CREATE INDEX IF NOT EXISTS idx_datasets_owner_created ON datasets(owner_id, created_at DESC)")
            db.commit()

    @staticmethod
    def _owner(owner_id: str | None = None) -> str:
        return owner_id or current_user()

    def register(self, dataset: Any, owner_id: str | None = None) -> None:
        """Insert a manifest owned by the current request identity."""
        owner = self._owner(owner_id)
        created_at = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.path) as db:
            existing = db.execute("SELECT owner_id FROM datasets WHERE dataset_id=?", (dataset.dataset_id,)).fetchone()
            if existing and existing[0] != owner:
                raise DatasetAccessError("Dataset belongs to another user.")
            db.execute(
                """INSERT INTO datasets
                    (dataset_id,fingerprint,filename,path,size_bytes,row_count,column_count,created_at,status,profile_json,mappings_json,owner_id)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(dataset_id) DO UPDATE SET
                        fingerprint=excluded.fingerprint,
                        filename=excluded.filename,
                        path=excluded.path,
                        size_bytes=excluded.size_bytes,
                        row_count=excluded.row_count,
                        column_count=excluded.column_count,
                        status=excluded.status
                """,
                (dataset.dataset_id, dataset.sha256, dataset.filename, str(dataset.path), dataset.size_bytes, dataset.row_count, dataset.column_count, created_at, "STORED", None, None, owner),
            )
            db.commit()

    def save_profile(self, dataset_id: str, profile: Any) -> None:
        with sqlite3.connect(self.path) as db:
            if not self._owned(db, dataset_id):
                raise DatasetAccessError("Dataset not found.")
            db.execute("UPDATE datasets SET profile_json=? WHERE dataset_id=?", (json.dumps(profile.model_dump(mode="json")), dataset_id))
            db.commit()

    def save_mappings(self, dataset_id: str, mappings: dict[str, str]) -> None:
        with sqlite3.connect(self.path) as db:
            if not self._owned(db, dataset_id):
                raise DatasetAccessError("Dataset not found.")
            db.execute("UPDATE datasets SET mappings_json=? WHERE dataset_id=?", (json.dumps(mappings), dataset_id))
            db.commit()

    def _owned(self, db: sqlite3.Connection, dataset_id: str, owner_id: str | None = None) -> bool:
        row = db.execute("SELECT owner_id FROM datasets WHERE dataset_id=?", (dataset_id,)).fetchone()
        return bool(row and row[0] == self._owner(owner_id))

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

    def get(self, dataset_id: str, owner_id: str | None = None) -> dict[str, Any] | None:
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM datasets WHERE dataset_id=? AND owner_id=?", (dataset_id, self._owner(owner_id))).fetchone()
        return dict(row) if row else None

    def list(self, limit: int = 50, owner_id: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 200))
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM datasets WHERE owner_id=? ORDER BY created_at DESC LIMIT ?", (self._owner(owner_id), limit)).fetchall()
        return [dict(row) for row in rows]


registry = DatasetRegistry()
