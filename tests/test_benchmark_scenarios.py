import csv

from scripts.benchmark import SCHEMA_SCENARIOS, make_fixture, run


def test_scenario_fixture_headers_match_mapping(tmp_path):
    for scenario, mappings in SCHEMA_SCENARIOS.items():
        path = tmp_path / f"{scenario}.csv"
        make_fixture(path, rows=5, seed=7, scenario=scenario)
        with path.open(newline="", encoding="utf-8") as handle:
            headers = next(csv.reader(handle))
        assert tuple(headers) == tuple(mappings)


def test_run_uses_selected_schema_scenario():
    for scenario in SCHEMA_SCENARIOS:
        result = run(rows=20, seed=123, scenario=scenario)
        assert result["fixture"]["scenario"] == scenario
        assert result["local"]["rows"] == 20
