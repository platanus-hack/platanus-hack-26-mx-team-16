from typing import Any
from uuid import UUID

from src.common.database.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummaryORM,
)
from src.common.domain.enums.run_summary import NarrativeStatus, Verdict
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    SignalSnapshot,
    WorkflowAnalysisRunSummary,
)


def build_workflow_analysis_run_summary(orm: WorkflowAnalysisRunSummaryORM) -> WorkflowAnalysisRunSummary:
    return WorkflowAnalysisRunSummary(
        uuid=orm.uuid,
        workflow_analysis_run_id=orm.workflow_analysis_run_id,
        tenant_id=orm.tenant_id,
        verdict=Verdict(orm.verdict),
        signals=[SignalSnapshot.model_validate(signal) for signal in (orm.signals or []) if isinstance(signal, dict)],
        signals_by_polarity=dict(orm.signals_by_polarity or {}),
        signals_by_severity=dict(orm.signals_by_severity or {}),
        confidence_score=float(orm.confidence_score) if orm.confidence_score is not None else None,
        blocking_failures=[_to_uuid(v) for v in (orm.blocking_failures or [])],
        degraded_rules=[_to_uuid(v) for v in (orm.degraded_rules or [])],
        output=orm.output,
        output_provenance=orm.output_provenance,
        output_schema_snapshot=orm.output_schema_snapshot,
        synthesis_template_snapshot=orm.synthesis_template_snapshot,
        narrative_status=NarrativeStatus(orm.narrative_status),
        narrative_error=orm.narrative_error,
        model=orm.model,
        provider=orm.provider,
        input_hash=orm.input_hash,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def _to_uuid(value: Any) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))
