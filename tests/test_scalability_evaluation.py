from scripts.scalability_evaluation import run_scalability


def test_scalability_protocol_is_reproducible_in_shape() -> None:
    first = run_scalability((20, 10, 20), seed=7, repeats=1)
    second = run_scalability((20, 10, 20), seed=7, repeats=1)
    assert first["protocol"] == "local_scalability_v1"
    assert first["sizes"] == [10, 20]
    assert first["sizes"] == second["sizes"]
    assert first["seed"] == second["seed"] == 7
    assert len(first["records"]) == 2
    assert [r["rows"] for r in first["records"]] == [10, 20]
    assert all(r["rows_per_second"] > 0 for r in first["records"])
    assert all(r["size_multiplier"] >= 1 for r in first["records"])
    assert all(r["elapsed_multiplier"] >= 0 for r in first["records"])


def test_scalability_rejects_invalid_repeat_budget() -> None:
    try:
        run_scalability((10,), repeats=6)
    except ValueError as exc:
        assert "repeats" in str(exc)
    else:
        raise AssertionError("expected bounded repeat validation")
