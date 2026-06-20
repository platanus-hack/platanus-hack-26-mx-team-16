from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel

from src.common.application.helpers.encoding import decode_base64, encode_base64
from src.common.domain.interfaces.presenter import Presenter
from src.common.settings import settings


class Pagination(BaseModel):
    next_cursor: str | None = None
    limit: int | None = None

    @classmethod
    def from_page(cls, page: "Page[Any]") -> Self:
        return cls(
            next_cursor=page.next_cursor,
            limit=page.limit,
        )


class PageIndex(BaseModel):
    value: datetime | None = None
    uuid: UUID | None = None

    @property
    def to_base64(self) -> str | None:
        if not self.value or not self.uuid:
            return None
        return encode_base64(f"{self.value.isoformat()}|{self.uuid}")

    @classmethod
    def from_base64(cls, base64: str) -> "PageIndex":
        decoded_value = decode_base64(base64)
        value, uuid = decoded_value.split("|")
        return cls(
            value=datetime.fromisoformat(value),
            uuid=UUID(uuid),
        )

    @classmethod
    def initial(cls) -> "PageIndex":
        return cls(value=None, uuid=None)


class Page[T](BaseModel):
    next_cursor: str | None = None
    items: list[T] | None = None
    limit: int = settings.PAGINATION_PAGE_SIZE

    def __post_init__(self):
        self.items = self.items or []

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "next_cursor": self.next_cursor,  # Fixed: was self.page_size
            "items": self.items,
        }

    @classmethod
    def empty(
        cls,
        page_size: int = settings.PAGINATION_PAGE_SIZE,
        items: list[T] | None = None,
    ) -> "Page[T]":
        return cls(
            next_cursor=None,
            items=items or [],
            limit=page_size,  # Added limit parameter
        )

    def apply_presenter(self, presenter_class: type[Presenter[T]]) -> None:
        self.items = [presenter_class(item).to_dict for item in self.items]
