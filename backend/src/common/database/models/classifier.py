from uuid import UUID

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base
from src.common.database.mixins.tenants import UUIDTenantTimestampMixin


class ClassifierORM(Base, UUIDTenantTimestampMixin):
    """Clasificador custom por tenant (phases-config · F3 · D-C). Referenciado
    por slug desde ``classify_pages.classifier``; resuelto en ``resolve_classifier``."""

    __tablename__ = "classifiers"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_classifiers_tenant_slug"),)

    slug: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    def __repr__(self) -> str:
        return f"<ClassifierORM(slug={self.slug}, kind={self.kind})>"
