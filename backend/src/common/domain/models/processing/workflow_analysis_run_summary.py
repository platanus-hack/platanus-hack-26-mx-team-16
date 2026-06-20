"""WorkflowAnalysisRunSummary — consolidated artifact per analysis run (synthesis spec §3)."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.run_summary import NarrativeStatus, Verdict


class SignalSnapshot(BaseModel):
    """Frozen-in-time copy of a VerdictSignal — kept on the summary for audit."""

    rule_id: UUID
    kind: str
    severity: str
    polarity: str
    weight: float = 1.0
    detail: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="ignore")


class WorkflowAnalysisRunSummary(BaseModel):
    """One summary per `WorkflowAnalysisRun`."""

    uuid: UUID = Field(default_factory=uuid4)
    workflow_analysis_run_id: UUID = Field(...)
    tenant_id: UUID = Field(...)

    # Deterministic layer
    verdict: Verdict = Field(default=Verdict.REVIEW)
    signals: list[SignalSnapshot] = Field(default_factory=list)
    signals_by_polarity: dict[str, int] = Field(default_factory=dict)
    signals_by_severity: dict[str, int] = Field(default_factory=dict)
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    blocking_failures: list[UUID] = Field(default_factory=list)
    degraded_rules: list[UUID] = Field(default_factory=list)

    # Synthesis layer
    output: dict[str, Any] | None = Field(default=None)
    # E2 · spec case-output §4.5: Citations per output field, keyed by JSON
    # Pointer (e.g. {"/total": [Citation, ...]}).
    output_provenance: dict[str, Any] | None = Field(default=None)
    output_schema_snapshot: dict[str, Any] | None = Field(default=None)
    synthesis_template_snapshot: str | None = Field(default=None)
    narrative_status: NarrativeStatus = Field(default=NarrativeStatus.PENDING)
    narrative_error: str | None = Field(default=None)

    # Reproducibility
    model: str | None = Field(default=None, max_length=128)
    provider: str | None = Field(default=None, max_length=64)
    input_hash: str = Field(..., min_length=1, max_length=64)

    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(from_attributes=True, extra="ignore")
