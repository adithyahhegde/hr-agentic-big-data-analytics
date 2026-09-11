from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "external-spark-validation.yml"


def test_external_spark_workflow_is_manual_and_requires_target_secret():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "HR_ANALYTICS_SPARK_MASTER: ${{ secrets.HR_ANALYTICS_SPARK_MASTER }}" in text
    assert "test -n \"$HR_ANALYTICS_SPARK_MASTER\"" in text
    assert "Local/loopback Spark masters are not accepted." in text


def test_external_spark_workflow_does_not_echo_sensitive_target_endpoint():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "parsed.hostname}:{parsed.port}" not in text
    assert "Target Spark master TCP endpoint is reachable." in text
    assert "Configured Spark driver host is present." in text
    assert "Configured Spark driver bind address is present." in text


def test_external_spark_workflow_requires_driver_version_and_reusable_validator():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "SPARK_VALIDATION_VERSION: ${{ inputs.spark_version }}" in text
    assert 'pyspark==${SPARK_VALIDATION_VERSION}' in text
    assert "python scripts/validate_external_spark_evidence.py artifacts/external-spark.json" in text
