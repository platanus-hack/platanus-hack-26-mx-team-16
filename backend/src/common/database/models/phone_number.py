from sqlalchemy import Boolean, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.common.database.mixins.common import Base, UUIDTimestampMixin


class PhoneNumberORM(Base, UUIDTimestampMixin):
    __tablename__ = "phone_numbers"
    __table_args__ = (
        UniqueConstraint(
            "dial_code",
            "phone_number",
            name="uq_phone_numbers_dial_code_phone_number",
        ),
    )

    iso_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )
    dial_code: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        index=True,
    )
    phone_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )
    prefix: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        default=None,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    @property
    def display_phone_number(self) -> str:
        if self.prefix:
            return f"+{self.dial_code} {self.prefix} {self.phone_number}"
        return f"+{self.dial_code} {self.phone_number}"

    def __repr__(self) -> str:
        return f"<PhoneNumber {self.display_phone_number}>"

    def __str__(self) -> str:
        return self.display_phone_number
