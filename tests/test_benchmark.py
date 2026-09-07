import csv
from pathlib import Path

from scripts.benchmark import MAPPINGS, make_fixture, run


def test_benchmark_fixture_is_reproducible(tmp_path: Path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    make_fixture(first, rows=25, seed=42)
    make_fixture(second, rows=25, seed=42)
    assert first.read_bytes() == second.read_bytes()


def test_benchmark_fixture_contains_only_aggregate_safe_columns(tmp_path: Path):
    path = tmp_path / "fixture.csv"
    make_fixture(path, rows=5, seed=7)
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert tuple(rows[0]) == tuple(MAPPINGS)
    assert len(rows) == 6
    assert rows[1][0] == "1"


def test_benchmark_run_is_reproducible_at_metadata_level():
    first = run(rows=10, seed=123)
    second = run(rows=10, seed=123)
    assert first["fixture"] == second["fixture"]
    assert first["routing"] == second["routing"]
    assert first["local"]["rows"] == second["local"]["rows"] == 10
    assert first["local"]["duplicate_rows"] == second["local"]["duplicate_rows"] == 0
    assert "spark" in first
