from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "ephemeral-spark-validation.yml").read_text(encoding="utf-8")
EVALUATION_WORKFLOW = (ROOT / ".github" / "workflows" / "evaluation.yml").read_text(encoding="utf-8")
EXTERNAL_WORKFLOW = (ROOT / ".github" / "workflows" / "external-spark-validation.yml").read_text(encoding="utf-8")
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_ephemeral_spark_workflow_uses_worker_compatible_runtime_provisioning():
    assert "actions/setup-python@v5" in WORKFLOW
    assert "python-version: '3.10'" in WORKFLOW
    assert "actions/setup-java@v5" in WORKFLOW
    assert "java-version: '17'" in WORKFLOW
    assert "apt-get install" not in WORKFLOW
    assert "python3.11" not in WORKFLOW
    assert "cache: maven" not in WORKFLOW
    assert 'requires-python = ">=3.10"' in PYPROJECT


def test_all_spark_evaluation_workflows_match_supported_python_runtime():
    assert "python-version: '3.10'" in EVALUATION_WORKFLOW
    assert "python-version: '3.10'" in EXTERNAL_WORKFLOW
    assert "python-version: '3.11'" not in EVALUATION_WORKFLOW
    assert "python-version: '3.11'" not in EXTERNAL_WORKFLOW


def test_evaluation_workflow_runs_when_project_metadata_changes():
    assert "- 'pyproject.toml'" in EVALUATION_WORKFLOW
    assert "- 'pyproject.toml'" in WORKFLOW


def test_ephemeral_spark_workflow_uses_explicit_pinned_spark_processes():
    assert "apache/spark:3.5.8-python3" in WORKFLOW
    assert "org.apache.spark.deploy.master.Master" in WORKFLOW
    assert "org.apache.spark.deploy.worker.Worker" in WORKFLOW
    assert "spark://spark-master:7077" in WORKFLOW
    assert "--cores 2 --memory 2g" in WORKFLOW


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


def test_manual_external_workflow_keeps_target_cluster_gate():
    assert "HR_ANALYTICS_SPARK_MASTER: ${{ secrets.HR_ANALYTICS_SPARK_MASTER }}" in EXTERNAL_WORKFLOW
    assert "Require a non-local target cluster" in EXTERNAL_WORKFLOW
    assert "socket.create_connection" in EXTERNAL_WORKFLOW
    assert "external_spark_scalability_v2" in EXTERNAL_WORKFLOW
    assert "aggregates_match_local_baseline" in EXTERNAL_WORKFLOW
