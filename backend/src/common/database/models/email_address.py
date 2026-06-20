from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin


class EmailAddressORM(Base, UUIDTimestampMixin):
    __tablename__ = "email_addresses"

    email: Mapped[str] = mapped_column(
        String(254),
        nullable=False,
        unique=True,
        index=True,
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<EmailAddress {self.email}>"

    def __str__(self) -> str:
        return self.email
