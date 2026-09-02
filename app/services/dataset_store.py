"""Process-local dataset storage for the M4 execution boundary.

Uploaded CSVs are streamed to local disk rather than retained in application
memory. Durable persistence belongs to the later persistence phase.
"""
from __future__ import annotations

import csv
import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


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

    def save_upload(self, dataset_id: str, filename: str, stream: BinaryIO, max_bytes: int) -> StoredDataset:
        path = self._root / f"{dataset_id}.csv"
        total = 0
        digest = hashlib.sha256()
        with path.open("wb") as output:
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    path.unlink(missing_ok=True)
                    raise ValueError("The uploaded file exceeds the configured execution size limit.")
                digest.update(chunk)
                output.write(chunk)
        if total == 0:
            path.unlink(missing_ok=True)
            raise ValueError("The uploaded dataset is empty.")
        row_count, column_count = self._count_csv(path)
        dataset = StoredDataset(dataset_id, path, filename, total, row_count, column_count, digest.hexdigest())
        self._datasets[dataset_id] = dataset
        return dataset

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
        return self._datasets.get(dataset_id)


store = DatasetStore()
