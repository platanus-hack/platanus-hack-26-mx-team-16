"""SQLAlchemy implementation of WorkflowAnalysisRunSummaryRepository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummaryORM,
)
from src.common.domain.enums.run_summary import NarrativeStatus
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.run_summary.errors import SummaryNotFoundError
from src.workflows.domain.run_summary.repositories.run_summary import (
    WorkflowAnalysisRunSummaryRepository,
)
from src.workflows.infrastructure.builders.analysis_run_summary import build_workflow_analysis_run_summary


class SQLWorkflowAnalysisRunSummaryRepository(WorkflowAnalysisRunSummaryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_run(self, run_id: UUID, tenant_id: UUID) -> WorkflowAnalysisRunSummary | None:
        stmt = select(WorkflowAnalysisRunSummaryORM).where(
            WorkflowAnalysisRunSummaryORM.workflow_analysis_run_id == run_id,
            WorkflowAnalysisRunSummaryORM.tenant_id == tenant_id,
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_workflow_analysis_run_summary(orm) if orm else None

    async def upsert(self, summary: WorkflowAnalysisRunSummary) -> WorkflowAnalysisRunSummary:
        async with atomic_transaction(self.session):
            payload = _serialize(summary)
            stmt = (
                pg_insert(WorkflowAnalysisRunSummaryORM)
                .values(**payload)
                .on_conflict_do_update(
                    index_elements=["workflow_analysis_run_id"],
                    set_={
                        "verdict": payload["verdict"],
                        "signals": payload["signals"],
                        "signals_by_polarity": payload["signals_by_polarity"],
                        "signals_by_severity": payload["signals_by_severity"],
                        "confidence_score": payload["confidence_score"],
                        "blocking_failures": payload["blocking_failures"],
                        "degraded_rules": payload["degraded_rules"],
                        "narrative_status": payload["narrative_status"],
                        "input_hash": payload["input_hash"],
                        "updated_at": datetime.now(UTC),
                    },
                )
                .returning(WorkflowAnalysisRunSummaryORM)
            )
            orm = (await self.session.execute(stmt)).scalar_one()
            await self.session.flush()
        return build_workflow_analysis_run_summary(orm)

    async def update_narrative(
        self,
        run_id: UUID,
        tenant_id: UUID,
        *,
        status: NarrativeStatus,
        output: dict | None = None,
        output_provenance: dict | None = None,
        output_schema_snapshot: dict | None = None,
        synthesis_template_snapshot: str | None = None,
        narrative_error: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        input_hash: str | None = None,
    ) -> WorkflowAnalysisRunSummary:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowAnalysisRunSummaryORM).where(
                WorkflowAnalysisRunSummaryORM.workflow_analysis_run_id == run_id,
                WorkflowAnalysisRunSummaryORM.tenant_id == tenant_id,
            )
            try:
                orm = (await self.session.execute(stmt)).scalar_one()
            except NoResultFound as exc:
                raise SummaryNotFoundError(str(run_id)) from exc

            orm.narrative_status = status.value
            if output is not None:
                orm.output = output
            if output_provenance is not None:
                orm.output_provenance = output_provenance
            if output_schema_snapshot is not None:
                orm.output_schema_snapshot = output_schema_snapshot
            if synthesis_template_snapshot is not None:
                orm.synthesis_template_snapshot = synthesis_template_snapshot
            orm.narrative_error = narrative_error
            if model is not None:
                orm.model = model
            if provider is not None:
                orm.provider = provider
            if input_hash is not None:
                orm.input_hash = input_hash
            orm.updated_at = datetime.now(UTC)

            await self.session.flush()
            await self.session.refresh(orm)
        return build_workflow_analysis_run_summary(orm)

    async def delete_by_run(self, run_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowAnalysisRunSummaryORM).where(
                WorkflowAnalysisRunSummaryORM.workflow_analysis_run_id == run_id,
                WorkflowAnalysisRunSummaryORM.tenant_id == tenant_id,
            )
            orm = (await self.session.execute(stmt)).scalar_one_or_none()
            if orm is None:
                return
            await self.session.delete(orm)
            await self.session.flush()


def _serialize(summary: WorkflowAnalysisRunSummary) -> dict[str, Any]:
    return {
        "uuid": summary.uuid,
        "tenant_id": summary.tenant_id,
        "workflow_analysis_run_id": summary.workflow_analysis_run_id,
        "verdict": summary.verdict.value,
        "signals": [s.model_dump(mode="json") for s in summary.signals],
        "signals_by_polarity": summary.signals_by_polarity,
        "signals_by_severity": summary.signals_by_severity,
        "confidence_score": summary.confidence_score,
        "blocking_failures": [str(uid) for uid in summary.blocking_failures],
        "degraded_rules": [str(uid) for uid in summary.degraded_rules],
        "output": summary.output,
        "output_provenance": summary.output_provenance,
        "output_schema_snapshot": summary.output_schema_snapshot,
        "synthesis_template_snapshot": summary.synthesis_template_snapshot,
        "narrative_status": summary.narrative_status.value,
        "narrative_error": summary.narrative_error,
        "model": summary.model,
        "provider": summary.provider,
        "input_hash": summary.input_hash,
    }
