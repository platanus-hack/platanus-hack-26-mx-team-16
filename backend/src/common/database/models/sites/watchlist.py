"""``watchlist`` table — private per-user watchlist (06-data-model §3.6).

The **global** watchlist is not materialized: it is ``sites.is_gov``.
"""

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin


class WatchlistORM(Base, UUIDTimestampMixin):
    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "site_id", name="uq_watchlist_user_site"),
    )

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
    monitor: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
