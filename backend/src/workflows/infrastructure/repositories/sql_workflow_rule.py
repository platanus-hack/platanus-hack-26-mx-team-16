"""SQLAlchemy implementation of WorkflowRuleRepository (spec §10.3)."""

from uuid import UUID

from sqlalchemy import case, func, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.processing.workflow_rule import WorkflowRuleORM
from src.common.domain.exceptions.workflow_rules import WorkflowRuleNotFoundError
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.infrastructure.builders.workflow_rule import build_workflow_rule


class SQLWorkflowRuleRepository(WorkflowRuleRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, rule_id: UUID, tenant_id: UUID) -> WorkflowRule | None:
        stmt = select(WorkflowRuleORM).where(
            WorkflowRuleORM.uuid == rule_id,
            WorkflowRuleORM.tenant_id == tenant_id,
        )
        orm = (await self.session.execute(stmt)).scalar_one_or_none()
        return build_workflow_rule(orm) if orm else None

    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[WorkflowRule]:
        stmt = (
            select(WorkflowRuleORM)
            .where(
                WorkflowRuleORM.workflow_id == workflow_id,
                WorkflowRuleORM.tenant_id == tenant_id,
            )
            .order_by(WorkflowRuleORM.position.asc(), WorkflowRuleORM.created_at.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return [build_workflow_rule(orm) for orm in rows]

    async def create(self, rule: WorkflowRule) -> WorkflowRule:
        async with atomic_transaction(self.session):
            next_position_stmt = select(func.coalesce(func.max(WorkflowRuleORM.position) + 1, 0)).where(
                WorkflowRuleORM.workflow_id == rule.workflow_id,
                WorkflowRuleORM.tenant_id == rule.tenant_id,
            )
            next_position = (await self.session.execute(next_position_stmt)).scalar_one()

            orm = WorkflowRuleORM(
                uuid=rule.uuid,
                tenant_id=rule.tenant_id,
                workflow_id=rule.workflow_id,
                name=rule.name,
                slug=rule.slug,
                position=next_position,
                is_active=rule.is_active,
                kind=rule.kind,
                prompt=rule.prompt,
                # E5 · regla condicional (gotcha: columna nueva ⇒ create() Y update()).
                when_expr=rule.when,
                config=rule.config,
                scope=rule.scope,
                knowledge_refs=list(rule.knowledge_refs or []),
                current_compilation_id=rule.current_compilation_id,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_workflow_rule(orm)

    async def update(self, rule: WorkflowRule) -> WorkflowRule:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowRuleORM).where(
                WorkflowRuleORM.uuid == rule.uuid,
                WorkflowRuleORM.tenant_id == rule.tenant_id,
            )
            try:
                orm = (await self.session.execute(stmt)).scalar_one()
            except NoResultFound as exc:
                raise WorkflowRuleNotFoundError(str(rule.uuid)) from exc

            orm.name = rule.name
            orm.is_active = rule.is_active
            orm.kind = rule.kind
            orm.prompt = rule.prompt
            # E5 · regla condicional (update persiste la entidad COMPLETA).
            orm.when_expr = rule.when
            orm.config = rule.config
            orm.scope = rule.scope
            orm.knowledge_refs = list(rule.knowledge_refs or [])
            orm.current_compilation_id = rule.current_compilation_id

            await self.session.flush()
            await self.session.refresh(orm)
        return build_workflow_rule(orm)

    async def delete(self, rule_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowRuleORM).where(
                WorkflowRuleORM.uuid == rule_id,
                WorkflowRuleORM.tenant_id == tenant_id,
            )
            try:
                orm = (await self.session.execute(stmt)).scalar_one()
            except NoResultFound as exc:
                raise WorkflowRuleNotFoundError(str(rule_id)) from exc
            await self.session.delete(orm)
            await self.session.flush()

    async def reorder(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        ordered_rule_ids: list[UUID],
    ) -> list[WorkflowRule]:
        async with atomic_transaction(self.session):
            position_case = case(
                {rid: idx for idx, rid in enumerate(ordered_rule_ids)},
                value=WorkflowRuleORM.uuid,
            )
            stmt = (
                update(WorkflowRuleORM)
                .where(
                    WorkflowRuleORM.workflow_id == workflow_id,
                    WorkflowRuleORM.tenant_id == tenant_id,
                    WorkflowRuleORM.uuid.in_(ordered_rule_ids),
                )
                .values(position=position_case)
            )
            await self.session.execute(stmt)
            await self.session.flush()
        return await self.list_by_workflow(workflow_id, tenant_id)

    async def set_current_compilation(
        self,
        rule_id: UUID,
        tenant_id: UUID,
        compilation_id: UUID | None,
    ) -> WorkflowRule:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowRuleORM).where(
                WorkflowRuleORM.uuid == rule_id,
                WorkflowRuleORM.tenant_id == tenant_id,
            )
            try:
                orm = (await self.session.execute(stmt)).scalar_one()
            except NoResultFound as exc:
                raise WorkflowRuleNotFoundError(str(rule_id)) from exc
            orm.current_compilation_id = compilation_id
            await self.session.flush()
            await self.session.refresh(orm)
        return build_workflow_rule(orm)
