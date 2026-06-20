"""``agentic_surface`` table — detected agentic surface inventory (06-data-model §3.4).

Independent of whether the surface was actually probed. ``inferred_model`` is
best-effort (NULL when the model is not exposed).
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin


class AgenticSurfaceORM(Base, UUIDTimestampMixin):
    __tablename__ = "agentic_surface"

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
    type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # chatbot | prompt_input | search_ai
    vendor: Mapped[str | None] = mapped_column(String(100), nullable=True, default=None)
    location_url: Mapped[str] = mapped_column(Text, nullable=False)
    inferred_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default=None
    )  # only with hard signal
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
