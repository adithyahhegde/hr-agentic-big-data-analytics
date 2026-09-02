from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    info = "INFO"
    warning = "WARNING"
    blocking = "BLOCKING"
    critical = "CRITICAL"


class RuleStatus(str, Enum):
    passed = "PASSED"
    warning = "WARNING"
    failed = "FAILED"


class Issue(BaseModel):
    code: str
    severity: Severity
    message: str
    column: str | None = None


class NumericStats(BaseModel):
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    zeros_count: int = 0
    negatives_count: int = 0


class ColumnProfile(BaseModel):
    source_name: str
    normalized_name: str
    inferred_type: str
    non_null_count: int
    null_count: int
    missing_percentage: float = 0.0
    unique_count: int
    uniqueness_ratio: float = 0.0
    sample_values: list[str] = Field(default_factory=list)
    numeric_stats: NumericStats | None = None


class MappingCandidate(BaseModel):
    canonical_field: str
    confidence: float = Field(ge=0, le=1)
    decision: str
    evidence: list[str]
    alternatives: list[str] = Field(default_factory=list)
    name_score: float = 0.0
    type_score: float = 0.0
    value_score: float = 0.0
    profile_score: float = 0.0


class QualityRuleResult(BaseModel):
    rule_name: str
    category: str
    status: RuleStatus
    severity: Severity
    message: str
    column: str | None = None
    metric_value: float | None = None
    threshold: float | None = None


class DataQualityMetrics(BaseModel):
    total_cells: int
    missing_cells: int
    completeness_rate: float
    duplicate_row_count: int
    duplicate_row_rate: float
    clean_row_count: int
    clean_row_rate: float
    constant_column_count: int


class DataQualityReport(BaseModel):
    health_score: float
    metrics: DataQualityMetrics
    rules: list[QualityRuleResult] = Field(default_factory=list)
    summary_by_severity: dict[str, int] = Field(default_factory=dict)


class DatasetProfile(BaseModel):
    dataset_id: str | None = None
    row_count: int
    column_count: int
    duplicate_row_count: int
    columns: list[ColumnProfile]
    mappings: dict[str, MappingCandidate]
    issues: list[Issue]
    data_quality: DataQualityReport | None = None
    llm_used: bool = False
    schema_version: str = ""
    dataset_fingerprint: str = ""


class SchemaAcceptanceRequest(BaseModel):
    mappings: dict[str, str]


class Capability(BaseModel):
    objective: str
    status: str
    reasons: list[str]


class SchemaAcceptanceResponse(BaseModel):
    dataset_id: str
    mappings: dict[str, str]
    capabilities: list[Capability]


class WorkloadRoutingRequest(BaseModel):
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    estimated_bytes: int | None = Field(default=None, ge=0)
    file_count: int = Field(default=1, ge=1)
    requires_distributed: bool = False


class WorkloadRoutingResponse(BaseModel):
    engine: str
    row_count: int
    column_count: int
    estimated_bytes: int | None = None
    file_count: int
    requires_distributed: bool
    policy: dict[str, int]


class DatasetExecutionResponse(BaseModel):
    dataset_id: str
    status: str
    engine: str
    row_count: int
    column_count: int
    size_bytes: int
    dataset_fingerprint: str
    warnings: list[str] = Field(default_factory=list)
