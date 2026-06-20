"""SQLAlchemy implementation of HumanTaskRepository (F6)."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.application.helpers.datetimes import utc_now
from src.common.database.models.human_task import HumanTaskORM
from src.common.domain.enums.human_tasks import HumanTaskStatus
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.models.human_task import HumanTask
from src.workflows.domain.repositories.human_task import HumanTaskRepository
from src.workflows.infrastructure.builders.human_task import build_human_task


class SQLHumanTaskRepository(HumanTaskRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert(self, task: HumanTask) -> HumanTask:
        async with atomic_transaction(self.session):
            existing = (
                await self.session.execute(select(HumanTaskORM).where(HumanTaskORM.task_key == task.task_key))
            ).scalar_one_or_none()
            if existing is not None:
                return build_human_task(existing)  # idempotent across workflow replays
            orm = HumanTaskORM(
                uuid=task.uuid,
                tenant_id=task.tenant_id,
                task_key=task.task_key,
                kind=task.kind.value,
                status=task.status.value,
                assignee_mode=task.assignee_mode.value,
                audience=task.audience,
                workflow_id=task.workflow_id,
                case_id=task.case_id,
                pipeline_run_id=task.pipeline_run_id,
                payload=task.payload,
                expires_at=task.expires_at,
                # E5 · revisión multinivel + claim (gotcha: columna nueva ⇒
                # persistirla en todos los caminos de escritura).
                stage=task.stage,
                claimed_by=task.claimed_by,
                claimed_at=task.claimed_at,
            )
            self.session.add(orm)
            await self.session.flush()
            await self.session.refresh(orm)
        return build_human_task(orm)

    async def find_by_id(self, task_id: UUID, tenant_id: UUID) -> HumanTask | None:
        orm = (
            await self.session.execute(
                select(HumanTaskORM).where(HumanTaskORM.uuid == task_id, HumanTaskORM.tenant_id == tenant_id)
            )
        ).scalar_one_or_none()
        return build_human_task(orm) if orm else None

    async def find_by_key(self, task_key: str) -> HumanTask | None:
        orm = (
            await self.session.execute(select(HumanTaskORM).where(HumanTaskORM.task_key == task_key))
        ).scalar_one_or_none()
        return build_human_task(orm) if orm else None

    async def resolve(self, task_id: UUID, tenant_id: UUID, resolution: dict) -> HumanTask | None:
        """E5 §C5: UPDATE condicional (mismo patrón que ``claim``) — sólo escribe
        si la fila sigue ``pending``. 0 filas ⇒ re-lee la fila actual y la
        devuelve sin sobrescribir (el use case enruta por la rama idempotente
        "ya resuelta", re-señalando la resolución ALMACENADA). Esto cierra la
        carrera de dos resolves concurrentes (last-writer-wins) y el doble-submit:
        exactamente un resolve gana la escritura."""
        async with atomic_transaction(self.session):
            result = await self.session.execute(
                update(HumanTaskORM)
                .where(
                    HumanTaskORM.uuid == task_id,
                    HumanTaskORM.tenant_id == tenant_id,
                    HumanTaskORM.status == HumanTaskStatus.PENDING.value,
                )
                .values(resolution=resolution, status=HumanTaskStatus.RESOLVED.value)
                .returning(HumanTaskORM)
            )
            orm = result.scalar_one_or_none()
            if orm is not None:
                return build_human_task(orm)
            # 0 filas: la tarea no existe (este tenant) o ya fue resuelta por
            # otro resolve concurrente. Re-leemos para que el caller (use case)
            # distinga 404 (None) de "ya resuelta" y re-señale lo almacenado.
            existing = (
                await self.session.execute(
                    select(HumanTaskORM).where(
                        HumanTaskORM.uuid == task_id, HumanTaskORM.tenant_id == tenant_id
                    )
                )
            ).scalar_one_or_none()
        return build_human_task(existing) if existing else None

    async def list_open(self, tenant_id: UUID, audience: str | None = None) -> list[HumanTask]:
        stmt = select(HumanTaskORM).where(
            HumanTaskORM.tenant_id == tenant_id,
            HumanTaskORM.status == HumanTaskStatus.PENDING.value,
        )
        if audience is not None:
            stmt = stmt.where(HumanTaskORM.audience == audience)
        stmt = stmt.order_by(HumanTaskORM.created_at.asc())
        result = await self.session.execute(stmt)
        return [build_human_task(orm) for orm in result.scalars()]

    async def list_open_by_case(self, case_id: UUID, tenant_id: UUID) -> list[HumanTask]:
        stmt = (
            select(HumanTaskORM)
            .where(
                HumanTaskORM.case_id == case_id,
                HumanTaskORM.tenant_id == tenant_id,
                HumanTaskORM.status == HumanTaskStatus.PENDING.value,
            )
            .order_by(HumanTaskORM.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return [build_human_task(orm) for orm in result.scalars()]

    async def claim(self, task_id: UUID, tenant_id: UUID, actor: str) -> HumanTask | None:
        """E5 §3.2: UPDATE condicional (lock pesimista) — 0 filas ⇒ None."""
        async with atomic_transaction(self.session):
            result = await self.session.execute(
                update(HumanTaskORM)
                .where(
                    HumanTaskORM.uuid == task_id,
                    HumanTaskORM.tenant_id == tenant_id,
                    HumanTaskORM.status == HumanTaskStatus.PENDING.value,
                    (HumanTaskORM.claimed_by.is_(None)) | (HumanTaskORM.claimed_by == actor),
                )
                .values(claimed_by=actor, claimed_at=utc_now())
                .returning(HumanTaskORM)
            )
            orm = result.scalar_one_or_none()
        return build_human_task(orm) if orm else None

    async def release(
        self, task_id: UUID, tenant_id: UUID, actor: str, force: bool = False
    ) -> HumanTask | None:
        conditions = [HumanTaskORM.uuid == task_id, HumanTaskORM.tenant_id == tenant_id]
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
