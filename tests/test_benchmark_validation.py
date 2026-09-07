from pathlib import Path

import pytest

from scripts.benchmark import run_matrix


def test_benchmark_matrix_rejects_non_positive_sizes_before_execution():
    with pytest.raises(ValueError, match="positive"):
        run_matrix(sizes=(10, 0), seed=42)


def test_benchmark_matrix_rejects_negative_sizes_before_execution():
    with pytest.raises(ValueError, match="positive"):
        run_matrix(sizes=(-1, 10), seed=42)


def test_benchmark_matrix_rejects_empty_size_matrix():
    with pytest.raises(ValueError, match="at least one"):
        run_matrix(sizes=(), seed=42)
