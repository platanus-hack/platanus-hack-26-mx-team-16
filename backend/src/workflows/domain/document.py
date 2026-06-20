from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PageRange:
    from_page: int
    to_page: int

    @classmethod
    def from_dict(cls, data: dict) -> "PageRange":
        return cls(
            from_page=int(data["from"]),
            to_page=int(data["to"]),
        )


@dataclass(frozen=True)
class Document:
    document_id: UUID
    object_key: str
    page_range: PageRange | None = None
