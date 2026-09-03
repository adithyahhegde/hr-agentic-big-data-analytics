"""Persistent local dataset storage with a durable manifest registry."""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.config import get_settings
from app.services.dataset_registry import registry


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
        settings = get_settings()
        self._root = settings.data_dir / "datasets"
        self._root.mkdir(parents=True, exist_ok=True)
        self._datasets: dict[str, StoredDataset] = {}

    def save_upload(self, dataset_id: str, filename: str, stream: BinaryIO, max_bytes: int) -> StoredDataset:
        path = self._root / f"{dataset_id}.csv"
        total = 0
        digest = hashlib.sha256()
        try:
            with path.open("wb") as output:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("The uploaded file exceeds the configured execution size limit.")
                    digest.update(chunk)
                    output.write(chunk)
            if total == 0:
                raise ValueError("The uploaded dataset is empty.")
            row_count, column_count = self._count_csv(path)
            dataset = StoredDataset(dataset_id, path, filename, total, row_count, column_count, digest.hexdigest())
            self._datasets[dataset_id] = dataset
            registry.register(dataset)
            return dataset
        except Exception:
            path.unlink(missing_ok=True)
            raise

    @staticmethod
    def _count_csv(path: Path) -> tuple[int, int]:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                headers = next(reader, None)
                if not headers:
                    raise ValueError("The uploaded dataset must include a header row.")
                return sum(1 for _ in reader), len(headers)
        except UnicodeDecodeError as exc:
            raise ValueError("The CSV must be UTF-8 encoded.") from exc
        except csv.Error as exc:
            raise ValueError("The CSV could not be parsed. Check delimiters and quoting.") from exc

    def get(self, dataset_id: str) -> StoredDataset | None:
        dataset = self._datasets.get(dataset_id)
        if dataset:
            return dataset
        manifest = registry.get(dataset_id)
        if not manifest:
            return None
        path = Path(manifest["path"])
        if not path.exists():
            return None
        dataset = StoredDataset(
            dataset_id=manifest["dataset_id"], path=path, filename=manifest["filename"],
            size_bytes=int(manifest["size_bytes"]), row_count=int(manifest["row_count"]),
            column_count=int(manifest["column_count"]), sha256=manifest["fingerprint"],
        )
        self._datasets[dataset_id] = dataset
        return dataset

    def list(self, limit: int = 50) -> list[dict[str, object]]:
        return registry.list(limit)


store = DatasetStore()
