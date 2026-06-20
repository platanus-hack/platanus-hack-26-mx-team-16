"""SQLAlchemy implementation of StaffHumanTaskRepository (ADR 0001).

Queries cross-tenant explícitas y ACOTADAS: toda query fija
``stage='review_l1'`` + ``assignee_mode='internal_queue'`` — el staff jamás
ve tareas L2 ni EXTERNAL_CALLBACK. El claim es un UPDATE condicional
(lock pesimista, diseño E5 §3.2): 0 filas ⇒ el caller decide 404/409.
"""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.application.helpers.datetimes import utc_now
from src.common.database.models.human_task import HumanTaskORM
from src.common.database.models.tenants.tenant import TenantORM
from src.common.domain.enums.human_tasks import HumanTaskAssigneeMode, HumanTaskStatus
from src.common.infrastructure.helpers.database import atomic_transaction
from src.staff.domain.entities import StaffQueueItem
from src.staff.domain.repositories.staff_human_task import StaffHumanTaskRepository
from src.workflows.domain.models.human_task import HumanTask
from src.workflows.infrastructure.builders.human_task import build_human_task

_L1_STAGE = "review_l1"


def _l1_scope():
    """Filtro de alcance staff: SIEMPRE presente en toda query del repo."""
    return (
        HumanTaskORM.stage == _L1_STAGE,
        HumanTaskORM.assignee_mode == HumanTaskAssigneeMode.INTERNAL_QUEUE.value,
    )


class SQLStaffHumanTaskRepository(StaffHumanTaskRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_open_l1(
        self,
        tenant_id: UUID | None = None,
        status: str | None = "pending",
        limit: int = 200,
        kind: str | None = None,
    ) -> list[StaffQueueItem]:
        stmt = (
            select(HumanTaskORM, TenantORM.name, TenantORM.slug)
            .join(TenantORM, TenantORM.uuid == HumanTaskORM.tenant_id, isouter=True)
            .where(*_l1_scope())
        )
        if tenant_id is not None:
            stmt = stmt.where(HumanTaskORM.tenant_id == tenant_id)
        if status is not None:
            stmt = stmt.where(HumanTaskORM.status == status)
        # E6 §3: segmenta aprobaciones vs auditoría QA (ambos en el alcance L1).
        if kind is not None:
            stmt = stmt.where(HumanTaskORM.kind == kind)
        stmt = stmt.order_by(HumanTaskORM.created_at.asc()).limit(limit)
        result = await self.session.execute(stmt)
        return [
            StaffQueueItem(task=build_human_task(orm), tenant_name=name, tenant_slug=slug)
            for orm, name, slug in result.all()
        ]

    async def find_by_id(self, task_id: UUID) -> HumanTask | None:
        orm = (
            await self.session.execute(
                select(HumanTaskORM).where(HumanTaskORM.uuid == task_id, *_l1_scope())
            )
        ).scalar_one_or_none()
        return build_human_task(orm) if orm else None

    async def find_l1_task_by_case(self, case_id: UUID) -> HumanTask | None:
        # Gate de PII cross-tenant: existe alguna tarea L1 servible (cualquier
        # estado) ligada al caso. Preferimos la pendiente; si no, la más
        # reciente (un caso ya resuelto sigue siendo legítimo de inspeccionar).
        orm = (
            await self.session.execute(
                select(HumanTaskORM)
                .where(HumanTaskORM.case_id == case_id, *_l1_scope())
                .order_by(
                    (HumanTaskORM.status == HumanTaskStatus.PENDING.value).desc(),
                    HumanTaskORM.created_at.desc(),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return build_human_task(orm) if orm else None

    async def claim(self, task_id: UUID, actor: str) -> HumanTask | None:
        async with atomic_transaction(self.session):
            result = await self.session.execute(
                update(HumanTaskORM)
                .where(
                    HumanTaskORM.uuid == task_id,
                    *_l1_scope(),
                    HumanTaskORM.status == HumanTaskStatus.PENDING.value,
                    (HumanTaskORM.claimed_by.is_(None)) | (HumanTaskORM.claimed_by == actor),
                )
                .values(claimed_by=actor, claimed_at=utc_now())
                .returning(HumanTaskORM)
            )
            orm = result.scalar_one_or_none()
        return build_human_task(orm) if orm else None

    async def release(self, task_id: UUID, actor: str, force: bool = False) -> HumanTask | None:
        conditions = [HumanTaskORM.uuid == task_id, *_l1_scope()]
        if not force:
            conditions.append(HumanTaskORM.claimed_by == actor)
        async with atomic_transaction(self.session):
            result = await self.session.execute(
                update(HumanTaskORM)
                .where(*conditions)
                .values(claimed_by=None, claimed_at=None)
                .returning(HumanTaskORM)
            )
            orm = result.scalar_one_or_none()
        return build_human_task(orm) if orm else None
