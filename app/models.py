from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class Severity(str, Enum):
    info = "INFO"
    warning = "WARNING"
    blocking = "BLOCKING"


class Issue(BaseModel):
    code: str
    severity: Severity
    message: str
    column: str | None = None


class ColumnProfile(BaseModel):
    source_name: str
    normalized_name: str
    inferred_type: str
    non_null_count: int
    null_count: int
    unique_count: int
    sample_values: list[str] = Field(default_factory=list)


class MappingCandidate(BaseModel):
    canonical_field: str
    confidence: float = Field(ge=0, le=1)
    decision: str
    evidence: list[str]


class DatasetProfile(BaseModel):
    row_count: int
    column_count: int
    duplicate_row_count: int
    columns: list[ColumnProfile]
    mappings: dict[str, MappingCandidate]
    issues: list[Issue]
    llm_used: bool = False
