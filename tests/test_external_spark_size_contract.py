from __future__ import annotations

import pytest

import scripts.external_spark_validation as external_validation


@pytest.mark.parametrize("sizes", [[100, 100], [1000, 100, 1000]])
def test_external_validation_rejects_duplicate_sizes(sizes):
    with pytest.raises(ValueError, match="sizes must be unique"):
        external_validation._validate_sizes(sizes)


def test_external_validation_still_sorts_unique_sizes():
    assert external_validation._validate_sizes([10_000, 100, 1_000]) == [100, 1_000, 10_000]
