"""SQLAlchemy implementation of WorkflowRepository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.workspace import WorkflowORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.infrastructure.builders.workflow import build_workflow


class SQLWorkflowRepository(WorkflowRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, workflow_id: UUID, tenant_id: UUID) -> Workflow | None:
        stmt = select(WorkflowORM).where(
            WorkflowORM.uuid == workflow_id,
            WorkflowORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        if orm_instance is None:
            return None
        return build_workflow(orm_instance)

    async def list_by_tenant(self, tenant_id: UUID, industry_id: UUID | None = None) -> list[Workflow]:
        stmt = select(WorkflowORM).where(WorkflowORM.tenant_id == tenant_id)
        if industry_id is not None:
            stmt = stmt.where(WorkflowORM.industry_id == industry_id)
        stmt = stmt.order_by(WorkflowORM.created_at.desc())
        result = await self.session.execute(stmt)
        orm_instances = list(result.scalars())
        return [build_workflow(orm) for orm in orm_instances]

    async def create(self, workflow: Workflow) -> Workflow:
        async with atomic_transaction(self.session):
            orm_instance = WorkflowORM(
                uuid=workflow.uuid,
                tenant_id=workflow.tenant_id,
                industry_id=workflow.industry_id,
                pipeline_id=workflow.pipeline_id,
                created_by_id=workflow.created_by_id,
                name=workflow.name,
                slug=workflow.slug,
                access_type=workflow.access_type,
                selected_doc_types=workflow.selected_doc_types,
                kb_document_ids=workflow.kb_document_ids,
                per_doc_kb_ids=workflow.per_doc_kb_ids,
                structuring_model=workflow.structuring_model,
                llm_model=workflow.llm_model,
                case_noun=workflow.case_noun,
            )
            self.session.add(orm_instance)
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_workflow(orm_instance)

    async def update(self, workflow: Workflow) -> Workflow:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowORM).where(
                WorkflowORM.uuid == workflow.uuid,
                WorkflowORM.tenant_id == workflow.tenant_id,
            )
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                raise WorkflowNotFoundError(str(workflow.uuid))

            orm_instance.name = workflow.name
            # E6 · W4: el bundle import enlaza la receta y backfilla el slug.
            orm_instance.pipeline_id = workflow.pipeline_id
            if workflow.slug is not None:
                orm_instance.slug = workflow.slug
            orm_instance.access_type = workflow.access_type
            orm_instance.selected_doc_types = workflow.selected_doc_types
            orm_instance.kb_document_ids = workflow.kb_document_ids
            orm_instance.per_doc_kb_ids = workflow.per_doc_kb_ids
            orm_instance.structuring_model = workflow.structuring_model
            orm_instance.llm_model = workflow.llm_model
            orm_instance.analysis_reviewer_model = workflow.analysis_reviewer_model
            orm_instance.analysis_critic_model = workflow.analysis_critic_model
            orm_instance.analysis_consensus_samples = workflow.analysis_consensus_samples
            orm_instance.output_schema = workflow.output_schema
            orm_instance.synthesis_template = workflow.synthesis_template
            orm_instance.synthesis_enabled = workflow.synthesis_enabled
            orm_instance.webhook_url = workflow.webhook_url
            orm_instance.webhook_enabled = workflow.webhook_enabled
            orm_instance.webhook_secret = workflow.webhook_secret
            orm_instance.webhook_events = workflow.webhook_events
            orm_instance.case_noun = workflow.case_noun

            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_workflow(orm_instance)

    async def delete(self, workflow_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowORM).where(
                WorkflowORM.uuid == workflow_id,
                WorkflowORM.tenant_id == tenant_id,
            )
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                raise WorkflowNotFoundError(str(workflow_id))

            await self.session.delete(orm_instance)
            await self.session.flush()
