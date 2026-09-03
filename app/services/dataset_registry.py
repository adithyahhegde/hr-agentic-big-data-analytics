"""Durable dataset manifest independent of in-memory workflow state."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DatasetRegistry:
    def __init__(self, path: Path | str = "hr_analytics_history.sqlite3") -> None:
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
                status TEXT NOT NULL
            )""")
            db.commit()

    def register(self, dataset: Any) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("""INSERT OR REPLACE INTO datasets
                (dataset_id,fingerprint,filename,path,size_bytes,row_count,column_count,created_at,status)
                VALUES(?,?,?,?,?,?,?,?,?)""", (
                dataset.dataset_id, dataset.sha256, dataset.filename, str(dataset.path),
                dataset.size_bytes, dataset.row_count, dataset.column_count,
                datetime.now(timezone.utc).isoformat(), "STORED",
            ))
            db.commit()

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
