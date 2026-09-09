from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

from app.services.analytics import NUMERIC_FIELDS


def _spark_session(master: str | None = None):
    from pyspark.sql import SparkSession

    configured_master = master or os.getenv("HR_ANALYTICS_SPARK_MASTER") or "local[*]"
    return (
        SparkSession.builder
        .appName("hr-agentic-big-data-analytics")
        .master(configured_master)
        .config("spark.sql.shuffle.partitions", os.getenv("HR_ANALYTICS_SPARK_SHUFFLE_PARTITIONS", "200"))
        .getOrCreate()
    )


def _execution_metadata(spark, *, distributed: bool, input_mode: str | None = None) -> dict[str, Any]:
    """Return bounded Spark provenance useful for reproducible validation."""
    context = spark.sparkContext
    metadata: dict[str, Any] = {
        "engine": "SPARK",
        "distributed": distributed,
        "raw_rows_returned": False,
        "spark_version": getattr(spark, "version", None),
        "default_parallelism": int(context.defaultParallelism),
    }
    application_id = getattr(context, "applicationId", None)
    if application_id:
        metadata["application_id"] = application_id
    if input_mode is not None:
        metadata["input_mode"] = input_mode
    return metadata


def _canonicalize_dataframe(df, mappings: dict[str, str]):
    """Rename mapped source columns to canonical HR fields before aggregation.

    The application mapping contract is ``source_column -> canonical_field``.
    Performing the normalization once at the DataFrame boundary prevents later
    Spark expressions from accidentally referring to a canonical name that is
    not the physical CSV column (especially for headers containing spaces).
    """
    mapped_canonicals: dict[str, str] = {}
    current_columns = set(df.columns)
    for source, canonical in mappings.items():
        if canonical == "unknown" or source not in current_columns:
            continue
        if canonical in mapped_canonicals and mapped_canonicals[canonical] != source:
            raise ValueError(
                f"Multiple Spark source columns map to canonical field '{canonical}'"
            )
        if source == canonical:
            mapped_canonicals[canonical] = source
            continue
        if canonical in current_columns:
            raise ValueError(
                f"Spark mapping collision: source '{source}' cannot be renamed to existing column '{canonical}'"
            )
        df = df.withColumnRenamed(source, canonical)
        current_columns.remove(source)
        current_columns.add(canonical)
        mapped_canonicals[canonical] = source
    return df, tuple(sorted(mapped_canonicals))


def _number_columns(df, canonical_fields: Iterable[str]) -> dict[str, str]:
    """Return canonical numeric HR fields, regardless of Spark's inferred CSV type."""
    return {field: field for field in canonical_fields if field in NUMERIC_FIELDS}


def _numeric_expression(column):
    """Parse a canonical numeric field consistently with the local CSV path."""
    from pyspark.sql import functions as F

    cleaned = F.regexp_replace(F.trim(column.cast("string")), ",", "")
    return cleaned.cast("double")


def _analyze_dataframe(df, mappings: dict[str, str], max_categories: int = 5) -> dict[str, Any]:
    """Run the bounded descriptive aggregation over an existing Spark DataFrame."""
    from pyspark.sql import functions as F

    df, canonical_fields = _canonicalize_dataframe(df, mappings)
    row_count = df.count()

    missing = []
    numeric_summary = []
    categorical_summary = []

    numeric_fields = _number_columns(df, canonical_fields)
    for canonical in canonical_fields:
        column = F.col(canonical)
        if canonical in numeric_fields:
            valid_numeric = _numeric_expression(column)
            missing_count = df.filter(column.isNull() | (valid_numeric.isNull())).count()
        else:
            cleaned = F.trim(column.cast("string"))
            missing_count = df.filter(column.isNull() | (cleaned == "")).count()
        missing.append({
            "field": canonical,
            "missing": missing_count,
            "rate": round(missing_count / row_count, 4) if row_count else 0,
        })

    for canonical in sorted(numeric_fields):
        parsed = _numeric_expression(F.col(canonical)).alias("_numeric_value")
        stats = df.select(parsed).agg(
            F.count(F.col("_numeric_value")).alias("count"),
            F.min(F.col("_numeric_value")).alias("min"),
            F.max(F.col("_numeric_value")).alias("max"),
            F.avg(F.col("_numeric_value")).alias("mean"),
            F.stddev(F.col("_numeric_value")).alias("stddev"),
        ).first()
        count = int(stats["count"] or 0)
        if count == 0:
            continue
        numeric_summary.append({
            "field": canonical,
            "count": count,
            "min": float(stats["min"]) if stats["min"] is not None else None,
            "max": float(stats["max"]) if stats["max"] is not None else None,
            "mean": float(stats["mean"]) if stats["mean"] is not None else None,
            "stddev": float(stats["stddev"]) if stats["stddev"] is not None else None,
        })

    for canonical in sorted(canonical_fields):
        if canonical in numeric_fields:
            continue
        counts = (
            df.filter(F.col(canonical).isNotNull())
            .groupBy(F.col(canonical).cast("string").alias("value"))
            .count()
            .orderBy(F.desc("count"), F.asc("value"))
            .limit(max_categories)
            .collect()
        non_missing = df.filter(
            F.col(canonical).isNotNull() & (F.trim(F.col(canonical).cast("string")) != "")
        ).count()
        distinct = df.select(F.col(canonical).cast("string")).where(F.col(canonical).isNotNull()).distinct().count()
        categorical_summary.append({
            "field": canonical,
            "count": non_missing,
            "distinct": distinct,
            "top_values": [
                {
                    "value": row["value"],
                    "count": int(row["count"]),
                    "share": round(int(row["count"]) / non_missing, 4) if non_missing else 0,
                }
                for row in counts
            ],
        })

    duplicate_count = 0
    if df.columns and row_count:
        row_hash = F.sha2(F.to_json(F.struct(*[F.col(c) for c in df.columns])), 256)
        duplicate_count = int(
            df.withColumn("_row_hash", row_hash)
            .groupBy("_row_hash")
            .count()
            .filter(F.col("count") > 1)
            .select(F.sum(F.col("count") - 1))
            .first()[0]
            or 0
        )

    insights: list[dict[str, Any]] = []
    for item in missing:
        if item["rate"] >= 0.20:
            insights.append({
                "type": "DATA_QUALITY",
                "severity": "WARNING",
                "title": f"High missingness in {item['field']}",
                "evidence": f"{item['missing']:,} of {row_count:,} rows are missing for this mapped field.",
            })
    if duplicate_count:
        insights.append({
            "type": "DATA_QUALITY",
            "severity": "WARNING",
            "title": "Duplicate records detected",
            "evidence": f"{duplicate_count:,} duplicate rows were observed ({duplicate_count / row_count:.1%} of the dataset).",
        })

    attrition_source = "attrition" if "attrition" in canonical_fields else None
    if attrition_source:
        labels = F.lower(F.trim(F.col(attrition_source).cast("string")))
        total = df.filter(F.col(attrition_source).isNotNull() & (F.trim(F.col(attrition_source).cast("string")) != "")).count()
        positive = df.filter(labels.isin("yes", "y", "true", "1", "left", "terminated", "attrition")).count()
        if total and positive:
            insights.append({
                "type": "WORKFORCE",
                "severity": "INFO",
                "title": "Attrition signal available",
                "evidence": f"{positive:,} of {total:,} non-empty attrition labels are in the positive class ({positive / total:.1%}).",
            })

    return {
        "row_count": row_count,
        "duplicate_row_count": duplicate_count,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "missing_by_field": sorted(missing, key=lambda item: item["field"]),
        "insights": insights,
    }


def analyze_spark(path: Path, mappings: dict[str, str], max_categories: int = 5, master: str | None = None) -> dict[str, Any]:
    """Distributed descriptive analytics. Only bounded aggregates are collected."""
    spark = _spark_session(master)
    configured_master = master or os.getenv("HR_ANALYTICS_SPARK_MASTER") or "local[*]"
    df = spark.read.option("header", True).option("inferSchema", True).csv(str(path))
    result = _analyze_dataframe(df, mappings, max_categories=max_categories)
    result["execution"] = _execution_metadata(
        spark,
        distributed=not configured_master.startswith("local"),
        input_mode="path",
    )
    return result


def analyze_spark_csv_lines(
    lines: Iterable[str],
    mappings: dict[str, str],
    max_categories: int = 5,
    master: str | None = None,
    *,
    stop_session: bool = False,
) -> dict[str, Any]:
    """Analyze CSV text without requiring executor access to a driver's filesystem.

    ``stop_session`` is opt-in because normal application calls may intentionally
    reuse the Spark session. External validation enables it so repeated target-
    cluster measurements do not retain Spark resources between sizes.
    """
    spark = _spark_session(master)
    configured_master = master or os.getenv("HR_ANALYTICS_SPARK_MASTER") or "local[*]"
    try:
        materialized = list(lines)
        if not materialized:
            raise ValueError("CSV input must contain at least a header row")
        parallelism = max(1, min(len(materialized), spark.sparkContext.defaultParallelism * 2))
        rdd = spark.sparkContext.parallelize(materialized, parallelism)
        df = spark.read.option("header", True).option("inferSchema", True).csv(rdd)
        result = _analyze_dataframe(df, mappings, max_categories=max_categories)
        result["execution"] = _execution_metadata(
            spark,
            distributed=not configured_master.startswith("local"),
            input_mode="driver_parallelized_csv",
        )
        return result
    finally:
        if stop_session:
            spark.stop()
