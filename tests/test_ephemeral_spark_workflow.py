from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "ephemeral-spark-validation.yml").read_text(encoding="utf-8")
CI_WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
EVALUATION_WORKFLOW = (ROOT / ".github" / "workflows" / "evaluation.yml").read_text(encoding="utf-8")
EXTERNAL_WORKFLOW = (ROOT / ".github" / "workflows" / "external-spark-validation.yml").read_text(encoding="utf-8")
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


PYTHON_RUNTIME = "3.10"
SPARK_VALIDATION_VERSION = "3.5.8"


def test_ephemeral_spark_workflow_uses_worker_compatible_runtime_provisioning():
    assert "actions/setup-python@v6" in WORKFLOW
    assert f"python-version: '{PYTHON_RUNTIME}'" in WORKFLOW
    assert "actions/setup-java@v5" in WORKFLOW
    assert "java-version: '17'" in WORKFLOW
    assert "apt-get install" not in WORKFLOW
    assert "python3.11" not in WORKFLOW
    assert "cache: maven" not in WORKFLOW
    assert 'requires-python = ">=3.10"' in PYPROJECT


def test_all_python_workflows_match_supported_project_runtime():
    workflows = (CI_WORKFLOW, EVALUATION_WORKFLOW, EXTERNAL_WORKFLOW, WORKFLOW)
    for workflow in workflows:
        assert "actions/setup-python@v6" in workflow
        assert f"python-version: '{PYTHON_RUNTIME}'" in workflow
        assert "python-version: '3.11'" not in workflow


def test_workflows_use_current_node24_compatible_actions():
    workflows = (CI_WORKFLOW, EVALUATION_WORKFLOW, EXTERNAL_WORKFLOW, WORKFLOW)
    for workflow in workflows:
        assert "actions/checkout@v6" in workflow
        assert "actions/checkout@v4" not in workflow
        assert "actions/setup-python@v6" in workflow
        assert "actions/setup-python@v5" not in workflow


def test_evaluation_workflow_runs_when_project_metadata_changes():
    assert "- 'pyproject.toml'" in EVALUATION_WORKFLOW
    assert "- 'pyproject.toml'" in WORKFLOW


def test_ephemeral_spark_workflow_uses_explicit_pinned_spark_processes():
    assert f"SPARK_VALIDATION_VERSION: '{SPARK_VALIDATION_VERSION}'" in WORKFLOW
    assert f'"apache/spark:${{SPARK_VALIDATION_VERSION}}-python3"' in WORKFLOW
    assert "org.apache.spark.deploy.master.Master" in WORKFLOW
    assert "org.apache.spark.deploy.worker.Worker" in WORKFLOW
    assert "spark://spark-master:7077" in WORKFLOW
    assert "--cores 2 --memory 2g" in WORKFLOW


def test_ephemeral_spark_workflow_pins_driver_to_cluster_version():
    assert 'pyspark==${SPARK_VALIDATION_VERSION}' in WORKFLOW
    assert "import pyspark" in WORKFLOW
    assert "pyspark.__version__ == expected" in WORKFLOW
    assert "PySpark driver/cluster version contract" in WORKFLOW


def test_ephemeral_spark_workflow_validates_readiness_and_cleans_up():
    assert "socket.create_connection(('127.0.0.1', 7077), timeout=5)" in WORKFLOW
    assert "Successfully registered with master" in WORKFLOW
    assert "if: failure()" in WORKFLOW
    assert "docker logs spark-master || true" in WORKFLOW
    assert "docker logs spark-worker || true" in WORKFLOW
    assert "if: always()" in WORKFLOW
    assert "docker rm -f spark-worker spark-master || true" in WORKFLOW
    assert "docker network rm hr-spark-ci || true" in WORKFLOW


def test_ephemeral_spark_workflow_configures_routable_driver_and_evidence_contract():
    assert "RUNNER_IP=$(hostname -I | awk '{print $1}')" in WORKFLOW
    assert "case \"$RUNNER_IP\" in" in WORKFLOW
    assert "HR_ANALYTICS_SPARK_MASTER=spark://${RUNNER_IP}:7077" in WORKFLOW
    assert "HR_ANALYTICS_SPARK_DRIVER_HOST=host.docker.internal" in WORKFLOW
    assert "HR_ANALYTICS_SPARK_DRIVER_BIND_ADDRESS=0.0.0.0" in WORKFLOW
    assert "external_spark_scalability_v2" in WORKFLOW
    assert "aggregates_match_local_baseline" in WORKFLOW
    assert "raw_rows_returned" in WORKFLOW
    assert "rows_per_second" in WORKFLOW


def test_ephemeral_spark_workflow_requires_provenance_and_version_alignment():
    assert "data['source_revision'] == os.environ['GITHUB_SHA']" in WORKFLOW
    assert "data['source_revision'] != 'unknown'" in WORKFLOW
    assert "runtime']['python_version']" in WORKFLOW
    assert "runtime']['platform']" in WORKFLOW
    assert "len(run['fixture_sha256']) == 64" in WORKFLOW
    assert "run['fixture_schema']" in WORKFLOW
    assert "execution['spark_version'] == expected_version" in WORKFLOW
    assert "execution['input_mode'] == 'driver_parallelized_csv'" in WORKFLOW


def test_manual_external_workflow_keeps_target_cluster_gate():
    assert "HR_ANALYTICS_SPARK_MASTER: ${{ secrets.HR_ANALYTICS_SPARK_MASTER }}" in EXTERNAL_WORKFLOW
    assert "Require a non-local target cluster" in EXTERNAL_WORKFLOW
    assert "socket.create_connection" in EXTERNAL_WORKFLOW
    assert "external_spark_scalability_v2" in EXTERNAL_WORKFLOW
    assert "aggregates_match_local_baseline" in EXTERNAL_WORKFLOW


def test_manual_external_workflow_supports_routable_driver_configuration():
    assert "HR_ANALYTICS_SPARK_DRIVER_HOST: ${{ secrets.HR_ANALYTICS_SPARK_DRIVER_HOST }}" in EXTERNAL_WORKFLOW
    assert "HR_ANALYTICS_SPARK_DRIVER_BIND_ADDRESS: ${{ secrets.HR_ANALYTICS_SPARK_DRIVER_BIND_ADDRESS }}" in EXTERNAL_WORKFLOW
    assert 'os.environ.get("HR_ANALYTICS_SPARK_DRIVER_HOST", "").strip()' in EXTERNAL_WORKFLOW
    assert 'os.environ.get("HR_ANALYTICS_SPARK_DRIVER_BIND_ADDRESS", "").strip()' in EXTERNAL_WORKFLOW


def test_manual_external_workflow_pins_and_verifies_target_spark_runtime():
    assert "spark_version:" in EXTERNAL_WORKFLOW
    assert "default: '3.5.8'" in EXTERNAL_WORKFLOW
    assert "SPARK_VALIDATION_VERSION: ${{ inputs.spark_version }}" in EXTERNAL_WORKFLOW
    assert '"pyspark==${SPARK_VALIDATION_VERSION}"' in EXTERNAL_WORKFLOW
    assert "Verify PySpark driver version" in EXTERNAL_WORKFLOW
    assert "pyspark.__version__" in EXTERNAL_WORKFLOW
    assert "execution['spark_version'] == expected_version" in EXTERNAL_WORKFLOW
