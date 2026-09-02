"""Engine-neutral analytical execution primitives for M4.

Small workloads use local execution; scalable workloads use Spark. Spark is an
optional dependency so the application remains usable without a JVM.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.workload_router import ExecutionEngine, RoutingPolicy, WorkloadProfile, route_workload


@dataclass(frozen=True)
class ExecutionResult:
    engine: ExecutionEngine
    rows: int
    columns: int
    output_path: str | None = None
    warnings: tuple[str, ...] = ()


def _spark_session() -> Any:
    try:
        from pyspark.sql import SparkSession
    except ImportError as exc:
        raise RuntimeError("Spark execution was selected but pyspark is not installed.") from exc
    return SparkSession.builder.appName("HR-Agentic-Big-Data-Analytics").getOrCreate()


def read_csv(path: str | Path, profile: WorkloadProfile, policy: RoutingPolicy | None = None) -> Any:
    """Read CSV through the selected engine; Spark stays distributed."""
    engine = route_workload(profile, policy)
    if engine is ExecutionEngine.SPARK:
        spark = _spark_session()
        return spark.read.option("header", True).option("inferSchema", True).csv(str(path))

    import pandas as pd
    return pd.read_csv(path)


def write_parquet(frame: Any, path: str | Path, engine: ExecutionEngine) -> None:
    """Persist the analytical representation without collecting Spark data."""
    destination = str(path)
    if engine is ExecutionEngine.SPARK:
        frame.write.mode("overwrite").parquet(destination)
        return
    frame.to_parquet(destination, index=False)


def scalable_groupby(frame: Any, group_columns: list[str], aggregations: dict[str, str], engine: ExecutionEngine) -> Any:
    """Perform a bounded aggregation using the selected execution engine."""
    if not group_columns:
        raise ValueError("At least one group column is required.")
    if not aggregations:
        raise ValueError("At least one aggregation is required.")

    if engine is ExecutionEngine.SPARK:
        from pyspark.sql import functions as F
        allowed = {"count": F.count, "sum": F.sum, "avg": F.avg, "min": F.min, "max": F.max}
        expressions = []
        for column, operation in aggregations.items():
            if operation not in allowed:
                raise ValueError(f"Unsupported aggregation: {operation}")
            expressions.append(allowed[operation](F.col(column)).alias(f"{operation}_{column}"))
        return frame.groupBy(*group_columns).agg(*expressions)

    return frame.groupby(group_columns, dropna=False).agg(aggregations).reset_index()
