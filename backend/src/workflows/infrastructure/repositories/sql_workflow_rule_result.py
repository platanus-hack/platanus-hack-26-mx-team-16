"""SQLAlchemy implementation of WorkflowRuleResultRepository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.processing.workflow_rule_result import WorkflowRuleResultORM
from src.common.domain.models.processing.citation import Citation
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.rules.repositories.workflow_rule_result import (
    WorkflowRuleResultRepository,
)
from src.workflows.infrastructure.builders.workflow_rule_result import (
    build_workflow_rule_result,
)


def _serialize_document_refs(refs: dict) -> dict:
    """Cast UUID values inside document_refs to str for JSONB storage."""
    return {slug: (str(value) if isinstance(value, UUID) else value) for slug, value in refs.items()}


def _serialize_citations(citations: list[Citation]) -> list[dict]:
    return [c.model_dump(mode="json") for c in citations]


class SQLWorkflowRuleResultRepository(WorkflowRuleResultRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, result_id: UUID, tenant_id: UUID) -> WorkflowRuleResult | None:
        stmt = select(WorkflowRuleResultORM).where(
            WorkflowRuleResultORM.uuid == result_id,
            WorkflowRuleResultORM.tenant_id == tenant_id,
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_workflow_rule_result(orm) if orm else None

    async def list_by_run(self, run_id: UUID, tenant_id: UUID) -> list[WorkflowRuleResult]:
        stmt = (
            select(WorkflowRuleResultORM)
            .where(
                WorkflowRuleResultORM.workflow_analysis_run_id == run_id,
                WorkflowRuleResultORM.tenant_id == tenant_id,
            )
            .order_by(WorkflowRuleResultORM.created_at.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [build_workflow_rule_result(orm) for orm in rows]

    async def list_by_case(self, case_id: UUID, tenant_id: UUID) -> list[WorkflowRuleResult]:
        stmt = (
            select(WorkflowRuleResultORM)
            .where(
                WorkflowRuleResultORM.case_id == case_id,
                WorkflowRuleResultORM.tenant_id == tenant_id,
            )
            .order_by(WorkflowRuleResultORM.created_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [build_workflow_rule_result(orm) for orm in rows]

    async def upsert(self, result: WorkflowRuleResult) -> WorkflowRuleResult:
        async with atomic_transaction(self.session):
            payload = {
                "uuid": result.uuid,
                "tenant_id": result.tenant_id,
                "workflow_analysis_run_id": result.workflow_analysis_run_id,
                "rule_id": result.rule_id,
                "case_id": result.case_id,
                "kind": result.kind,
                "status": result.status.value,
                "output": result.output,
                "reasoning": result.reasoning,
                "citations": _serialize_citations(result.citations),
                "document_refs": _serialize_document_refs(result.document_refs),
                "document_refs_hash": result.document_refs_hash,
                "rendered_prompt": result.rendered_prompt,
                "evaluation_metadata": result.evaluation_metadata,
                "error": result.error,
            }
            stmt = pg_insert(WorkflowRuleResultORM).values(**payload)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_workflow_rule_results_run_rule_refs",
                set_={
                    "kind": stmt.excluded.kind,
                    "status": stmt.excluded.status,
                    "output": stmt.excluded.output,
                    "reasoning": stmt.excluded.reasoning,
                    "citations": stmt.excluded.citations,
                    "document_refs": stmt.excluded.document_refs,
                    "rendered_prompt": stmt.excluded.rendered_prompt,
                    "evaluation_metadata": stmt.excluded.evaluation_metadata,
                    "error": stmt.excluded.error,
                },
            ).returning(WorkflowRuleResultORM)
            orm = (await self.session.execute(stmt)).scalar_one()
            await self.session.flush()
        return build_workflow_rule_result(orm)
