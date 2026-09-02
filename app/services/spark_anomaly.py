"""Scalable anomaly screening for Spark-routed workloads.

This is deliberately a transparent statistical screen, not an Isolation Forest
replacement. It keeps employee-level records inside Spark and returns only
aggregate evidence.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def run_distributed_anomaly(path: Path, mappings: dict[str, str], features: list[str]) -> dict[str, Any]:
    try:
        from pyspark.sql import SparkSession, functions as F
    except ImportError as exc:
        raise RuntimeError("Distributed anomaly screening requires the optional 'bigdata' dependencies.") from exc

    spark = SparkSession.builder.appName("hr-agentic-anomaly").getOrCreate()
    df = spark.read.option("header", True).option("inferSchema", True).csv(str(path))
    canonical = {source: field for source, field in mappings.items() if field != "unknown"}
    numeric_types = {"int", "bigint", "double", "float", "smallint", "tinyint", "long", "decimal"}
    usable: dict[str, str] = {}
    for source, field in canonical.items():
        if field in {"employee_id", "employee_record_id", "manager_id"} or source not in df.columns:
            continue
        safe = f"c_{field}"
        if safe not in df.columns:
            df = df.withColumnRenamed(source, safe)
        usable[field] = safe
    numeric = [f for f in features if f in usable and dict(df.dtypes).get(usable[f]) in numeric_types]
    if len(numeric) < 2:
        raise ValueError("At least two numeric predictors are required for distributed anomaly screening.")
    for field in numeric:
        df = df.withColumn(usable[field], F.col(usable[field]).cast("double"))
    complete = df.dropna(subset=[usable[f] for f in numeric])
    stats = complete.agg(
        *[F.avg(usable[f]).alias(f"m_{f}") for f in numeric],
        *[F.stddev_pop(usable[f]).alias(f"s_{f}") for f in numeric],
    ).first()
    if stats is None:
        raise ValueError("No complete rows are available for distributed anomaly screening.")
    score = None
    active = 0
    for field in numeric:
        mean, std = stats[f"m_{field}"], stats[f"s_{field}"]
        if mean is None or std is None or float(std) == 0:
            continue
        active += 1
        component = F.abs((F.col(usable[field]) - F.lit(float(mean))) / F.lit(float(std)))
        score = component if score is None else F.greatest(score, component)
    if active < 2 or score is None:
        raise ValueError("At least two variable-variance numeric predictors are required for anomaly screening.")
    scored = complete.withColumn("__anomaly_score", score)
    total = scored.count()
    threshold = 3.0
    anomaly_count = scored.filter(F.col("__anomaly_score") >= threshold).count()
    summary = scored.agg(F.avg("__anomaly_score").alias("mean_score"), F.max("__anomaly_score").alias("max_score")).first()
    return {
        "objective": "anomaly_detection",
        "rows_used": int(total),
        "feature_fields": numeric,
        "anomaly_count": int(anomaly_count),
        "anomaly_rate": round(anomaly_count / total, 4) if total else 0.0,
        "threshold": threshold,
        "score_definition": "maximum absolute standardized deviation across confirmed numeric features",
        "score_summary": {"mean": round(float(summary["mean_score"]), 4), "max": round(float(summary["max_score"]), 4)},
        "method": "distributed_zscore_screen",
        "execution": {"engine": "SPARK", "distributed": True, "raw_rows_returned": False},
        "safeguards": ["confirmed features only", "identifier exclusion", "distributed aggregate statistics", "no employee-level anomaly records returned", "transparent threshold"],
    }
