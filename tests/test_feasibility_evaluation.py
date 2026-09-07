from scripts.feasibility_evaluation import OBJECTIVES, SCENARIOS, evaluate


def test_feasibility_evaluation_is_reproducible():
    first = evaluate((10, 20, 100), seed=42)
    second = evaluate((10, 20, 100), seed=42)
    assert first == second
    assert first["accuracy"]["pipeline"] == 1.0
    assert first["accuracy"]["pipeline"] > first["accuracy"]["baseline"]


def test_feasibility_evaluation_covers_small_and_sufficient_rows():
    result = evaluate((10, 20), seed=7)
    assert result["sizes"] == [10, 20]
    assert result["objectives"] == list(OBJECTIVES)
    assert len(result["records"]) == 2 * len(SCENARIOS)
    small = [r for r in result["records"] if r["rows"] == 10]
    assert all(not any(r["pipeline"].values()) for r in small)


def test_feasibility_evaluation_blocks_collision_scenarios():
    result = evaluate((100,), seed=1)
    blocked = {r["scenario"]: r for r in result["records"] if r["scenario"] in {"ambiguous", "leakage_prone"}}
    assert blocked
    assert all(not any(r["pipeline"].values()) for r in blocked.values())
    assert all(not any(r["expected"].values()) for r in blocked.values())
