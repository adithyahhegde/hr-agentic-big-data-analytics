from scripts.agent_reliability_evaluation import evaluate


def test_agent_reliability_protocol_is_deterministic():
    first = evaluate(42)
    second = evaluate(42)
    assert first == second
    assert first["protocol"] == "bounded_agent_reliability_v1"
    assert first["aggregate"]["scenario_count"] == 7


def test_agent_reliability_protocol_exercises_safe_abstention_paths():
    result = evaluate(42)
    records = {record["scenario"]: record for record in result["records"]}
    assert result["aggregate"]["safe_scenarios"] == 7
    assert records["valid"]["evidence_count"] >= 2
    assert records["blocked"]["plan_count"] == 0
    for name in ("unsupported_objective", "cross_dataset", "invalid_anomaly_share", "malformed_anomaly_share"):
        assert records[name]["evidence_count"] == 1
    assert records["evidence_overflow"]["evidence_count"] == 50


def test_agent_reliability_preserves_recommendation_citation_integrity():
    result = evaluate(42)
    assert all(record["citation_integrity"] for record in result["records"])
    assert all(record["bounded_evidence"] for record in result["records"])
