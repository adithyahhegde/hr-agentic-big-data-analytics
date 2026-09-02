"""Process-local dataset storage for the M4 execution boundary.

The store keeps uploaded CSVs on local disk rather than in memory. It is
intentionally process-local for the MVP; durable persistence belongs to the
persistence phase.
"""
from __future__ import annotations

import csv
import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StoredDataset:
    dataset_id: str
    path: Path
    filename: str
    size_bytes: int
    row_count: int
    column_count: int
    sha256: str


class DatasetStore:
    def __init__(self) -> None:
        self._root = Path(tempfile.mkdtemp(prefix="hr_analytics_"))
        self._datasets: dict[str, StoredDataset] = {}

    def save_csv(self, dataset_id: str, filename: str, payload: bytes) -> StoredDataset:
        if not payload:
            raise ValueError("The uploaded dataset is empty.")
        path = self._root / f"{dataset_id}.csv"
        path.write_bytes(payload)
        return self._register(dataset_id, path, filename)

    def _register(self, dataset_id: str, path: Path, filename: str) -> StoredDataset:
        sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        row_count, column_count = self._count_csv(path)
        dataset = StoredDataset(
            dataset_id=dataset_id,
            path=path,
            filename=filename,
            size_bytes=path.stat().st_size,
            row_count=row_count,
            column_count=column_count,
            sha256=sha256,
        )
        self._datasets[dataset_id] = dataset
        return dataset

    @staticmethod
    def _count_csv(path: Path) -> tuple[int, int]:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            try:
                headers = next(reader)
            except StopIteration as exc:
                raise ValueError("The uploaded dataset has no header row.") from exc
            rows = sum(1 for _ in reader)
        return rows, len(headers)

    def get(self, dataset_id: str) -> StoredDataset | None:
        return self._datasets.get(dataset_id)


store = DatasetStore()
