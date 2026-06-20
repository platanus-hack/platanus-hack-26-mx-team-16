from typing import TypeVar

from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.enums.base_enum import BaseEnum
from src.common.settings import settings

T = TypeVar("T", bound=BaseEnum)


class ListFilters(CamelCaseRequest):
    cursor: str | None = Field(default=None)
    limit: int = Field(default=settings.PAGINATION_PAGE_SIZE)

    @staticmethod
    def parse_enum_values(raw_values: str | None, enum_class: type[T]) -> list[T]:
        """Parse comma-separated string values into a list of enum instances.

        Args:
            raw_values: Comma-separated string of values (e.g., "CREATED,SUCCEEDED")
            enum_class: The enum class to parse values into

        Returns:
            List of enum instances matching the provided values
        """
        if not raw_values:
            return []

        values = raw_values.split(",")
        enum_instances = []

        for value in values:
            enum_instance = enum_class.from_value(value.strip())
            if enum_instance:
                enum_instances.append(enum_instance)

        return enum_instances


class OffsetListFilters(CamelCaseRequest):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
