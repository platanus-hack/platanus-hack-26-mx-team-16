from __future__ import annotations

from enum import Enum
from typing import Any, Self


class BaseEnum(Enum):
    """Provides the common functionalties to multiple model choices."""

    @classmethod
    def get_members(cls) -> list[Self]:
        return [tag for tag in cls if type(tag.value) in [int, str, float]]

    @classmethod
    def choices(cls) -> list[tuple[Any, Any]]:
        """Generate choice options for models."""
        return [(option.value, option.value) for option in cls if type(option.value) in [int, str, float]]

    @classmethod
    def values(cls) -> list[Any]:
        """Returns values from choices."""
        return [option.value for option in cls]

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return self.__str__()

    def __hash__(self) -> int:
        return hash(self.value)

    @classmethod
    def as_list(cls) -> list[str]:
        return [str(member.value) for member in cls]

    @classmethod
    def from_value(cls, value: str | int | None, default: Self | None = None) -> Self:
        if not value:
            return default

        for member in cls:
            if isinstance(member.value, str) and isinstance(value, str):
                if member.value.upper() == value.upper():
                    return member
            elif member.value == value:
                return member
        return default
