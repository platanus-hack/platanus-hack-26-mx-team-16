"""``scans`` table — one row per engine run (06-data-model §3.2).

The observable core of the worker and the leaderboard row. PK is a UUIDv4 (not a
serial) by security decision: prevents enumeration / IDOR over real findings.
All score columns are computed in deterministic Python (07-scoring) before they
touch the DB; the model only persists them.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CHAR,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin
from src.common.domain.enums.scans import ScanStatus, ScanVisibility


class ScanORM(Base, UUIDTimestampMixin):
    __tablename__ = "scans"
    __table_args__ = (
        # Idempotency of POST /scans: only one active scan per (site, level).
        # Partial unique index; created explicitly in the migration too.
        Index(
            "uq_scans_active_per_site_level",
            "site_id",
            "level",
            unique=True,
            postgresql_where=text("status IN ('queued','running')"),
        ),
        # Leaderboard order "worst first": grade ASC, penalty_raw DESC (§4).
        Index("ix_scans_leaderboard", "overall_grade", text("penalty_raw DESC")),
    )

    site_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sites.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=str(ScanStatus.QUEUED)
    )
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, default=str(ScanVisibility.PRIVATE)
    )

    requested_by: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True,  # gov anonymous seed scans
    )
    authorized: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    authorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # -- Observability / live-view on reload (§3.2) --
    progress: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    current_phase: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    tools_status: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=None)
    coverage: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=None)
    error: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # -- Scoring (computed in Python, 07-scoring) --
    web_score: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    agentic_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )
    overall_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )
    overall_grade: Mapped[str | None] = mapped_column(
        CHAR(1), nullable=True, default=None
    )  # A..F (includes E)
    agentic_status: Mapped[str | None] = mapped_column(
        String(25), nullable=True, default=None
    )
    penalty_raw: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )  # uncapped penalty, for leaderboard tie-break (§3.2)
    summary: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=None
    )  # serialized ExecutiveSummary from Opus (05 writes, 09 reads)

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    def __repr__(self) -> str:
        return f"<Scan {self.uuid} {self.level} {self.status}>"
