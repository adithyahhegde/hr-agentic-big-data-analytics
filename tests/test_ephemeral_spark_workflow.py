from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github" / "workflows" / "ephemeral-spark-validation.yml").read_text(encoding="utf-8")


def test_ephemeral_spark_workflow_uses_supported_runtime_provisioning():
    assert "actions/setup-python@v5" in WORKFLOW
    assert "python-version: '3.11'" in WORKFLOW
    assert "actions/setup-java@v4" in WORKFLOW
    assert "java-version: '17'" in WORKFLOW
    assert "apt-get install" not in WORKFLOW
    assert "python3.11" not in WORKFLOW


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


def test_ephemeral_spark_workflow_configures_driver_reachability_and_evidence_contract():
    assert "HR_ANALYTICS_SPARK_MASTER: spark://127.0.0.1:7077" in WORKFLOW
    assert "HR_ANALYTICS_SPARK_DRIVER_HOST: host.docker.internal" in WORKFLOW
    assert "HR_ANALYTICS_SPARK_DRIVER_BIND_ADDRESS: 0.0.0.0" in WORKFLOW
    assert "external_spark_scalability_v2" in WORKFLOW
    assert "aggregates_match_local_baseline" in WORKFLOW
    assert "raw_rows_returned" in WORKFLOW
    assert "rows_per_second" in WORKFLOW
