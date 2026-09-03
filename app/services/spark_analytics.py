from __future__ import annotations

from pathlib import Path
from typing import Any


def _spark_session():
    from pyspark.sql import SparkSession

    return (
        SparkSession.builder
        .appName("hr-agentic-big-data-analytics")
        .master("local[*]")
        .config("spark.sql.shuffle.partitions", "200")
        .getOrCreate()
    )


def _number_columns(df, canonical_to_source: dict[str, str]) -> dict[str, str]:
    numeric_types = {"tinyint", "smallint", "int", "bigint", "float", "double", "decimal"}
    result: dict[str, str] = {}
    for canonical, source in canonical_to_source.items():
        dtype = dict(df.dtypes).get(source, "")
        if any(dtype.startswith(prefix) for prefix in numeric_types):
            result[canonical] = source
    return result


def analyze_spark(path: Path, mappings: dict[str, str], max_categories: int = 5) -> dict[str, Any]:
    """Distributed descriptive analytics. Only bounded aggregates are collected."""
    from pyspark.sql import functions as F

    source_to_canonical = {source: canonical for source, canonical in mappings.items() if canonical != "unknown"}
    canonical_to_source = {canonical: source for source, canonical in source_to_canonical.items()}
    spark = _spark_session()
    df = spark.read.option("header", True).option("inferSchema", True).csv(str(path))
    row_count = df.count()

    missing = []
    numeric_summary = []
    categorical_summary = []

    for canonical, source in canonical_to_source.items():
        if source not in df.columns:
            continue
        cleaned = F.trim(F.col(source).cast("string"))
        missing_count = df.filter(F.col(source).isNull() | (cleaned == "")).count()
        missing.append({"field": canonical, "missing": missing_count, "rate": round(missing_count / row_count, 4) if row_count else 0})

    numeric_fields = _number_columns(df, canonical_to_source)
    for canonical, source in sorted(numeric_fields.items()):
        stats = df.select(
            F.count(F.col(source)).alias("count"),
            F.min(F.col(source)).alias("min"),
            F.max(F.col(source)).alias("max"),
            F.avg(F.col(source)).alias("mean"),
            F.stddev(F.col(source)).alias("stddev"),
        ).first()
        numeric_summary.append({
            "field": canonical,
            "count": int(stats["count"] or 0),
            "min": float(stats["min"]) if stats["min"] is not None else None,
            "max": float(stats["max"]) if stats["max"] is not None else None,
            "mean": float(stats["mean"]) if stats["mean"] is not None else None,
            "stddev": float(stats["stddev"]) if stats["stddev"] is not None else None,
        })

    for canonical, source in sorted(canonical_to_source.items()):
        if canonical in numeric_fields:
            continue
        counts = (
            df.filter(F.col(source).isNotNull())
            .groupBy(F.col(source).cast("string").alias("value"))
            .count()
            .orderBy(F.desc("count"), F.asc("value"))
            .limit(max_categories)
            .collect()
        )
        non_missing = df.filter(F.col(source).isNotNull() & (F.trim(F.col(source).cast("string")) != "")).count()
        distinct = df.select(F.col(source).cast("string")).where(F.col(source).isNotNull()).distinct().count()
        categorical_summary.append({
            "field": canonical,
            "count": non_missing,
            "distinct": distinct,
            "top_values": [{"value": row["value"], "count": int(row["count"]), "share": round(int(row["count"]) / non_missing, 4) if non_missing else 0} for row in counts],
        })

    duplicate_count = 0
    if df.columns and row_count:
        row_hash = F.sha2(F.to_json(F.struct(*[F.col(c) for c in df.columns])), 256)
        duplicate_count = int(df.withColumn("_row_hash", row_hash).groupBy("_row_hash").count().filter(F.col("count") > 1).select(F.sum(F.col("count") - 1)).first()[0] or 0)

    insights: list[dict[str, Any]] = []
    for item in missing:
        if item["rate"] >= 0.20:
            insights.append({"type": "DATA_QUALITY", "severity": "WARNING", "title": f"High missingness in {item['field']}", "evidence": f"{item['missing']:,} of {row_count:,} rows are missing for this mapped field."})
    if duplicate_count:
        insights.append({"type": "DATA_QUALITY", "severity": "WARNING", "title": "Duplicate records detected", "evidence": f"{duplicate_count:,} duplicate rows were observed ({duplicate_count / row_count:.1%} of the dataset)."})

    attrition_source = canonical_to_source.get("attrition")
    if attrition_source and attrition_source in df.columns:
        labels = F.lower(F.trim(F.col(attrition_source).cast("string")))
        total = df.filter(F.col(attrition_source).isNotNull() & (F.trim(F.col(attrition_source).cast("string")) != "")).count()
        positive = df.filter(labels.isin("yes", "y", "true", "1", "left", "terminated", "attrition")).count()
        if total and positive:
            insights.append({"type": "WORKFORCE", "severity": "INFO", "title": "Attrition signal available", "evidence": f"{positive:,} of {total:,} non-empty attrition labels are in the positive class ({positive / total:.1%})."})

    return {
        "row_count": row_count,
        "duplicate_row_count": duplicate_count,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "missing_by_field": sorted(missing, key=lambda item: item["field"]),
        "insights": insights,
        "execution": {"engine": "SPARK", "distributed": True, "raw_rows_returned": False},
    }
