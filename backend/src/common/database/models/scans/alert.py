"""``alerts`` table — log of monitoring notifications sent (06-data-model §3.6).

``channel`` in {email, slack}. The channel behavior itself is defined in
08-ranking-watchlists §5.1; this is just the emitted-notification log.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin


class AlertORM(Base, UUIDTimestampMixin):
    __tablename__ = "alerts"

    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sites.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("scans.uuid", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # email | slack
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
