"""SQLAlchemy implementation of WorkflowEventRepository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.workflow_event import WorkflowEventORM
from src.common.domain.enums.webhooks import WebhookEventType, WorkflowEventDeliveryStatus
from src.common.domain.models.workflow_event import WorkflowEvent
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.repositories.workflow_event import WorkflowEventRepository
from src.workflows.infrastructure.builders.workflow_event import build_workflow_event

_RETRYABLE_STATUSES = (
    WorkflowEventDeliveryStatus.PENDING.value,
    WorkflowEventDeliveryStatus.FAILED.value,
)


class SQLWorkflowEventRepository(WorkflowEventRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, event: WorkflowEvent) -> WorkflowEvent:
        async with atomic_transaction(self.session):
            orm_instance = WorkflowEventORM(
                uuid=event.uuid,
                tenant_id=event.tenant_id,
                event_id=event.event_id,
                event_type=event.event_type.value,
                workflow_id=event.workflow_id,
                processing_job_id=event.processing_job_id,
                document_id=event.document_id,
                destination_id=event.destination_id,
                idempotency_key=event.idempotency_key,
                document_status=event.document_status,
                payload=event.payload,
                delivery_status=event.delivery_status.value,
                attempts=event.attempts,
                last_attempt_at=event.last_attempt_at,
                delivered_at=event.delivered_at,
                response_status=event.response_status,
                last_error=event.last_error,
            )
            self.session.add(orm_instance)
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_workflow_event(orm_instance)

    async def update(self, event: WorkflowEvent) -> WorkflowEvent:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowEventORM).where(WorkflowEventORM.uuid == event.uuid)
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                msg = f"WorkflowEvent {event.uuid} not found"
                raise ValueError(msg) from None

            orm_instance.delivery_status = event.delivery_status.value
            orm_instance.attempts = event.attempts
            orm_instance.last_attempt_at = event.last_attempt_at
            orm_instance.delivered_at = event.delivered_at
            orm_instance.response_status = event.response_status
            orm_instance.last_error = event.last_error

            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_workflow_event(orm_instance)

    async def find_by_id(self, event_uuid: UUID, tenant_id: UUID) -> WorkflowEvent | None:
        stmt = select(WorkflowEventORM).where(
            WorkflowEventORM.uuid == event_uuid,
            WorkflowEventORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        return build_workflow_event(orm_instance) if orm_instance else None

    async def find_by_unique(
        self,
        document_id: UUID,
        event_type: WebhookEventType,
        idempotency_key: str,
    ) -> WorkflowEvent | None:
        stmt = select(WorkflowEventORM).where(
            WorkflowEventORM.document_id == document_id,
            WorkflowEventORM.event_type == event_type.value,
            WorkflowEventORM.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        return build_workflow_event(orm_instance) if orm_instance else None

    async def find_by_unique_destination(
        self,
        document_id: UUID,
        event_type: WebhookEventType,
        idempotency_key: str,
        destination_id: UUID | None,
    ) -> WorkflowEvent | None:
        stmt = select(WorkflowEventORM).where(
            WorkflowEventORM.document_id == document_id,
            WorkflowEventORM.event_type == event_type.value,
            WorkflowEventORM.idempotency_key == idempotency_key,
        )
        if destination_id is None:
            stmt = stmt.where(WorkflowEventORM.destination_id.is_(None))
        else:
            stmt = stmt.where(WorkflowEventORM.destination_id == destination_id)
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        return build_workflow_event(orm_instance) if orm_instance else None

    async def list_by_set(self, processing_job_id: UUID, tenant_id: UUID) -> list[WorkflowEvent]:
        stmt = (
            select(WorkflowEventORM)
            .where(
                WorkflowEventORM.processing_job_id == processing_job_id,
                WorkflowEventORM.tenant_id == tenant_id,
            )
            .order_by(WorkflowEventORM.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return [build_workflow_event(orm) for orm in result.scalars()]

    async def list_by_workflow(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        delivery_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowEvent]:
        stmt = select(WorkflowEventORM).where(
            WorkflowEventORM.workflow_id == workflow_id,
            WorkflowEventORM.tenant_id == tenant_id,
        )
        if delivery_status is not None:
            stmt = stmt.where(WorkflowEventORM.delivery_status == delivery_status)
        stmt = stmt.order_by(WorkflowEventORM.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [build_workflow_event(orm) for orm in result.scalars()]

    async def list_by_destination(
        self,
        destination_id: UUID,
        tenant_id: UUID,
        delivery_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[WorkflowEvent]:
        stmt = select(WorkflowEventORM).where(
            WorkflowEventORM.destination_id == destination_id,
            WorkflowEventORM.tenant_id == tenant_id,
        )
        if delivery_status is not None:
            stmt = stmt.where(WorkflowEventORM.delivery_status == delivery_status)
        stmt = stmt.order_by(WorkflowEventORM.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return [build_workflow_event(orm) for orm in result.scalars()]

    async def list_for_retry(self, limit: int = 100) -> list[WorkflowEvent]:
        stmt = (
            select(WorkflowEventORM)
            .where(WorkflowEventORM.delivery_status.in_(_RETRYABLE_STATUSES))
            .order_by(WorkflowEventORM.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [build_workflow_event(orm) for orm in result.scalars()]
