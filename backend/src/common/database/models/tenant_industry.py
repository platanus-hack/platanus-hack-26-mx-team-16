from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin


class TenantIndustryORM(Base, UUIDTimestampMixin):
    __tablename__ = "tenant_industries"
    __table_args__ = (UniqueConstraint("tenant_id", "industry_id"),)

    tenant_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("tenants.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    industry_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("industries.uuid", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TenantIndustryORM(tenant={self.tenant_id}, industry={self.industry_id})>"
