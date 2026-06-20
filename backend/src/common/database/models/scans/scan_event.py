"""``scan_events`` table — MANDATORY live-view persistence (06-data-model §3.5).

The monotonic ``seq`` per scan is the single source of order and enables
deterministic replay on reload. ``UNIQUE (scan_id, seq)`` enforces it.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin


class ScanEventORM(Base, UUIDTimestampMixin):
    __tablename__ = "scan_events"
    __table_args__ = (
        # Single source of order; enables deterministic replay (§4).
        UniqueConstraint("scan_id", "seq", name="uq_scan_events_scan_seq"),
    )

    scan_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("scans.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # discriminant
    agent: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    tool: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    severity: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=None
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}", default=dict
    )
    progress: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )  # 0..100 on phase/score events
