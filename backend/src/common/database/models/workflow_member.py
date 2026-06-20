from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class WorkflowMemberORM(Base, UUIDTenantTimestampMixin):
    """An explicit per-workflow member grant.

    When a workflow's ``access_type`` is ``private`` only its members (plus the
    tenant owner and the workflow creator) may access it. ``role`` is stored for
    display and is not yet enforced at the endpoint level.
    """

    __tablename__ = "workflow_members"
    __table_args__ = (
        UniqueConstraint("workflow_id", "user_id", name="uq_workflow_member"),
        Index("ix_workflow_members_workflow", "workflow_id"),
        Index("ix_workflow_members_user_tenant", "user_id", "tenant_id"),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("workflows.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default="member")

    def __repr__(self) -> str:
        return f"<WorkflowMemberORM(workflow_id={self.workflow_id}, user_id={self.user_id}, role={self.role})>"
