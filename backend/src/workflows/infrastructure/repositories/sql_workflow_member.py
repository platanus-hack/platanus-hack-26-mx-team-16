"""SQLAlchemy implementation of WorkflowMemberRepository.

Member rows store only ``user_id`` + ``role``; reads left-join the member's
tenant-user / user / email records so the presenter can show name, email and
photo without a second round-trip.
"""

from uuid import UUID

from sqlalchemy import Row, Select, and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models import UserORM
from src.common.database.models.email_address import EmailAddressORM
from src.common.database.models.tenants.tenant_user import TenantUserORM
from src.common.database.models.workflow_member import WorkflowMemberORM
from src.common.domain.exceptions.processing import WorkflowMemberNotFoundError
from src.common.domain.models.workflow_member import WorkflowMember
from src.common.infrastructure.helpers.database import atomic_transaction
from src.workflows.domain.repositories.workflow_member import WorkflowMemberRepository
from src.workflows.infrastructure.builders.workflow_member import build_workflow_member


class SQLWorkflowMemberRepository(WorkflowMemberRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _enriched_query(workflow_id: UUID, tenant_id: UUID) -> Select:
        return (
            select(
                WorkflowMemberORM,
                TenantUserORM.first_name.label("tu_first"),
                TenantUserORM.last_name.label("tu_last"),
                TenantUserORM.photo.label("tu_photo"),
                TenantUserORM.is_owner.label("is_owner"),
                UserORM.first_name.label("u_first"),
                UserORM.last_name.label("u_last"),
                EmailAddressORM.email.label("email"),
            )
            .join(
                TenantUserORM,
                and_(
                    TenantUserORM.user_id == WorkflowMemberORM.user_id,
                    TenantUserORM.tenant_id == WorkflowMemberORM.tenant_id,
                ),
                isouter=True,
            )
            .join(UserORM, UserORM.uuid == WorkflowMemberORM.user_id, isouter=True)
            .join(EmailAddressORM, EmailAddressORM.uuid == UserORM.email_address_id, isouter=True)
            .where(
                WorkflowMemberORM.workflow_id == workflow_id,
                WorkflowMemberORM.tenant_id == tenant_id,
            )
        )

    @staticmethod
    def _build_from_row(row: Row) -> WorkflowMember:
        return build_workflow_member(
            row[0],
            first_name=row.tu_first or row.u_first,
            last_name=row.tu_last or row.u_last,
            email=row.email,
            photo=row.tu_photo,
            is_owner=bool(row.is_owner),
        )

    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[WorkflowMember]:
        stmt = self._enriched_query(workflow_id, tenant_id).order_by(WorkflowMemberORM.created_at.asc())
        result = await self.session.execute(stmt)
        return [self._build_from_row(row) for row in result.all()]

    async def find(self, workflow_id: UUID, user_id: UUID, tenant_id: UUID) -> WorkflowMember | None:
        stmt = self._enriched_query(workflow_id, tenant_id).where(WorkflowMemberORM.user_id == user_id)
        result = await self.session.execute(stmt)
        row = result.first()
        return self._build_from_row(row) if row is not None else None

    async def list_workflow_ids_for_user(self, user_id: UUID, tenant_id: UUID) -> list[UUID]:
        stmt = select(WorkflowMemberORM.workflow_id).where(
            WorkflowMemberORM.user_id == user_id,
            WorkflowMemberORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def add(self, member: WorkflowMember) -> WorkflowMember:
        async with atomic_transaction(self.session):
            orm_instance = WorkflowMemberORM(
                uuid=member.uuid,
                tenant_id=member.tenant_id,
                workflow_id=member.workflow_id,
                user_id=member.user_id,
                role=member.role,
            )
            self.session.add(orm_instance)
            await self.session.flush()
        enriched = await self.find(member.workflow_id, member.user_id, member.tenant_id)
        if enriched is None:  # pragma: no cover - row was just inserted
            raise WorkflowMemberNotFoundError(str(member.user_id))
        return enriched

    async def update_role(
        self, workflow_id: UUID, user_id: UUID, tenant_id: UUID, role: str
    ) -> WorkflowMember:
        async with atomic_transaction(self.session):
            stmt = select(WorkflowMemberORM).where(
                WorkflowMemberORM.workflow_id == workflow_id,
                WorkflowMemberORM.user_id == user_id,
                WorkflowMemberORM.tenant_id == tenant_id,
            )
            result = await self.session.execute(stmt)
            orm_instance = result.scalar_one_or_none()
            if orm_instance is None:
                raise WorkflowMemberNotFoundError(str(user_id))
            orm_instance.role = role
            await self.session.flush()
        enriched = await self.find(workflow_id, user_id, tenant_id)
        if enriched is None:  # pragma: no cover
            raise WorkflowMemberNotFoundError(str(user_id))
        return enriched

    async def remove(self, workflow_id: UUID, user_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = delete(WorkflowMemberORM).where(
                WorkflowMemberORM.workflow_id == workflow_id,
                WorkflowMemberORM.user_id == user_id,
                WorkflowMemberORM.tenant_id == tenant_id,
            )
            await self.session.execute(stmt)
