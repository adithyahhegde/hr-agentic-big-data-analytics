from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "external-spark-validation.yml").read_text(encoding="utf-8")


def test_external_spark_workflow_publishes_verified_evidence_summary():
    assert 'GITHUB_STEP_SUMMARY' in WORKFLOW
    assert '## External Spark validation' in WORKFLOW
    assert "data['source_revision']" in WORKFLOW
    assert "data['sizes']" in WORKFLOW
    assert 'default_parallelism' in WORKFLOW
    assert 'application_id' in WORKFLOW
    assert 'rows_per_second' in WORKFLOW


def test_external_spark_summary_is_after_evidence_validation():
    validation_pos = WORKFLOW.index('name: Validate evidence artifact')
    summary_pos = WORKFLOW.index('name: Summarize verified evidence')
    upload_pos = WORKFLOW.index('name: Upload validation artifact')
    assert validation_pos < summary_pos < upload_pos


def test_external_spark_summary_does_not_expose_raw_rows():
    summary = WORKFLOW.split('name: Summarize verified evidence', 1)[1].split('name: Upload validation artifact', 1)[0]
    assert 'raw_rows' not in summary
    assert 'employee_id' not in summary
