from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class PersonMixin:
    """Mixin for person information (first/last name)."""

    first_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )
    last_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class ProfileMixin(PersonMixin):
    """Extends PersonMixin with profile photo."""

    photo: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )
