"""``notification_prefs`` table — per-user channel preferences (06-data-model §3.6).

Intentionally breaks the UUID-PK pattern: the PK is the natural key ``user_id``
(1:1 with the user). Uses ``TimeStampedModelMixin`` only — do NOT "fix" this to a
UUID PK (spec §7.4). Account-level, not per-domain; the monitoring reads it to
decide which channels to emit (channels defined in 08-ranking-watchlists §5.1;
configured via ``PUT /me/alerts``).
"""

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, TimeStampedModelMixin


class NotificationPrefsORM(Base, TimeStampedModelMixin):
    __tablename__ = "notification_prefs"

    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="CASCADE"),
        primary_key=True,
    )
    email_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    slack_webhook_url: Mapped[str | None] = mapped_column(
        String(2048), nullable=True, default=None
    )
