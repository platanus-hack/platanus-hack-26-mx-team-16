"""``findings`` table — one row per deduplicated finding (06-data-model §3.3).

Identity is stable across scans via ``dedupe_key`` (a deterministic sha256),
enabling temporal monitoring: UPSERT by ``(site_id, dedupe_key)``; a finding that
stops reappearing flips to ``status='fixed'``. ``first_seen``/``last_seen`` are at
**SITE** level, not scan level, so monitoring survives between scans.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin
from src.common.domain.enums.scans import FindingStatus


class FindingORM(Base, UUIDTimestampMixin):
    __tablename__ = "findings"
    __table_args__ = (
        # UPSERT key for re-scan temporal monitoring (§4).
        UniqueConstraint("site_id", "dedupe_key", name="uq_findings_site_dedupe"),
    )

    scan_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("scans.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    site_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("sites.uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source: Mapped[str] = mapped_column(String(20), nullable=False)  # owasp | agentic
    tool: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False)  # A01.. / LLM01..
    title: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    cvss: Mapped[float | None] = mapped_column(Float, nullable=True, default=None)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}", default=dict
    )
    affected_url: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    endpoint: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    param: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    impact: Mapped[str] = mapped_column(Text, nullable=False)
    remediation: Mapped[str] = mapped_column(Text, nullable=False)
    references: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default="[]", default=list
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=str(FindingStatus.OPEN)
    )

    # Stable identity across scans (§3.3). VARCHAR (not CHAR) so short/legacy keys
    # are NOT space-padded to 64 on read — padding would break equality, ``notin_``
    # and the change-detection round-trip. A sha256 hex is exactly 64 chars anyway.
    dedupe_key: Mapped[str] = mapped_column(String(64), nullable=False)
    # Site-level temporal monitoring (§3.3) — survive between scans.
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Finding {self.severity} {self.category} {self.title[:32]!r}>"
