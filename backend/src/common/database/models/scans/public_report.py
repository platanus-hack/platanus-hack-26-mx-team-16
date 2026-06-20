"""``public_reports`` table — shareable report links (06-data-model §3.7).

``token`` is an opaque ``secrets.token_urlsafe(32)``, UNIQUE-indexed. TTL default
7 days. ``GET /r/{token}``: 404 if missing, 410 Gone if expired/revoked (12-api).
The public surface exposes the executive layer + findings WITHOUT exploitation
payloads (09-reporting).
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin


class PublicReportORM(Base, UUIDTimestampMixin):
    __tablename__ = "public_reports"

    token: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    scan_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("scans.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
