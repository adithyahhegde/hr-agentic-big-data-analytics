"""Deterministic routing between local and distributed analytical execution.

The router makes an execution-path decision from measurable workload properties.
It does not claim that a dataset is "big data" solely because it exceeds a
small arbitrary row count.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionEngine(str, Enum):
    LOCAL = "LOCAL"
    SPARK = "SPARK"


@dataclass(frozen=True)
class WorkloadProfile:
    row_count: int
    column_count: int
    estimated_bytes: int | None = None
    file_count: int = 1
    requires_distributed: bool = False


@dataclass(frozen=True)
class RoutingPolicy:
    """Engineering defaults; thresholds are configurable and not universal."""
    max_local_rows: int = 1_000_000
    max_local_bytes: int = 512 * 1024 * 1024
    max_local_columns: int = 500
    max_local_files: int = 32


def route_workload(profile: WorkloadProfile, policy: RoutingPolicy | None = None) -> ExecutionEngine:
    """Select LOCAL or SPARK without materialising the dataset."""
    policy = policy or RoutingPolicy()
    if profile.requires_distributed:
        return ExecutionEngine.SPARK
    if profile.row_count > policy.max_local_rows:
        return ExecutionEngine.SPARK
    if profile.estimated_bytes is not None and profile.estimated_bytes > policy.max_local_bytes:
        return ExecutionEngine.SPARK
    if profile.column_count > policy.max_local_columns:
        return ExecutionEngine.SPARK
    if profile.file_count > policy.max_local_files:
        return ExecutionEngine.SPARK
    return ExecutionEngine.LOCAL
