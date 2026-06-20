"""``sites`` table — catalogue of scanned domains (06-data-model §3.1)."""

from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin


class SiteORM(Base, UUIDTimestampMixin):
    __tablename__ = "sites"

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # is_gov is computed on insert (hostname endswith .gob.mx); NEVER from the
    # client. Source of the global gov leaderboard (08-ranking-watchlists).
    is_gov: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    country: Mapped[str | None] = mapped_column(String(2), nullable=True, default=None)
    owner_user_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("users.uuid", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Denormalized pointer to the latest scan (resolve current grade w/o subquery).
    # use_alter=True because of the circular reference sites <-> scans.
    latest_scan_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "scans.uuid",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_sites_latest_scan_id",
        ),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Site {self.hostname} gov={self.is_gov}>"
