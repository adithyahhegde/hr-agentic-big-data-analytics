from scripts.schema_mapping_evaluation import evaluate


def test_schema_mapping_evaluation_is_reproducible():
    first = evaluate(sizes=(20, 100), seed=42)
    second = evaluate(sizes=(20, 100), seed=42)
    assert first == second


def test_schema_mapping_evaluation_excludes_blocked_scenarios():
    result = evaluate(sizes=(20,), seed=42)
    blocked = {record["scenario"] for record in result["records"] if record["blocked"]}
    assert blocked == {"ambiguous", "leakage_prone"}
    assert result["aggregate"]["evaluated_columns"] > 0


def test_schema_mapping_evaluation_aggregate_matches_records():
    result = evaluate(sizes=(20,), seed=42)
    evaluated = [record for record in result["records"] if not record["blocked"]]
    assert result["aggregate"]["semantic_exact"] == sum(r["semantic_exact"] for r in evaluated)
    assert result["aggregate"]["baseline_exact"] == sum(r["baseline_exact"] for r in evaluated)
    assert result["aggregate"]["semantic_exact"] <= result["aggregate"]["evaluated_columns"]
    assert result["aggregate"]["baseline_exact"] <= result["aggregate"]["evaluated_columns"]


def test_schema_mapping_evaluation_reports_non_name_only_scenarios():
    result = evaluate(sizes=(20,), seed=42)
    records = {record["scenario"]: record for record in result["records"]}
    assert records["messy"]["semantic_accuracy"] is not None
    assert records["categorical"]["semantic_accuracy"] is not None
    assert records["messy"]["baseline_accuracy"] < records["messy"]["semantic_accuracy"] or records["categorical"]["baseline_accuracy"] < records["categorical"]["semantic_accuracy"]
