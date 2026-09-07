from pathlib import Path

from scripts.benchmark import MAPPINGS, make_fixture, run
from app.services.workload_router import ExecutionEngine


def test_benchmark_fixture_is_deterministic(tmp_path: Path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    make_fixture(first, rows=25, seed=7)
    make_fixture(second, rows=25, seed=7)
    assert first.read_bytes() == second.read_bytes()


def test_benchmark_fixture_has_expected_schema(tmp_path: Path):
    path = tmp_path / "fixture.csv"
    make_fixture(path, rows=10, seed=42)
    header = path.read_text(encoding="utf-8").splitlines()[0].split(",")
    assert header == list(MAPPINGS)


def test_benchmark_reports_local_execution_for_small_fixture():
    result = run(rows=100, seed=42)
    assert result["local"]["rows"] == 100
    assert result["local"]["duplicate_rows"] == 0
    assert result["routing"]["selected_engine"] == ExecutionEngine.LOCAL.value
