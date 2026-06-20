import base64
from dataclasses import dataclass
from typing import Any, Self

from src.common.domain.helpers.paths import (
    get_filename_from_path,
    remove_extension,
    remove_slash_from_path,
)


@dataclass
class InMemoryFile:
    file_path: str | None = None
    file_bytes: bytes | None = None
    file_base64: str | None = None

    def __post_init__(self):
        if not self.file_path:
            return
        if self.file_base64 and not self.file_bytes:
            self.file_bytes = base64.b64decode(self.file_base64)
        elif self.file_bytes and not self.file_base64:
            self.file_base64 = base64.b64encode(self.file_bytes).decode()

    @property
    def is_valid(self) -> bool:
        return bool(self.file_path and self.file_bytes)

    @property
    def has_content(self) -> bool:
        return bool(self.file_bytes or self.file_base64)

    @property
    def file_name(self) -> str | None:
        return get_filename_from_path(self.file_path) if self.file_path else None

    @property
    def raw_file_name(self) -> str:
        return remove_extension(self.file_name) if self.file_name else ""

    @property
    def file_key(self) -> str | None:
        return remove_slash_from_path(self.file_path) if self.file_path else None

    @property
    def is_procesable(self) -> bool:
        return self.is_valid and self.has_content

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "file_base64": self.file_base64,
        }

    @property
    def to_queue_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        file_bytes = data.get("file_bytes")
        file_base64 = data.get("file_base64")

        if file_bytes and not file_base64:
            file_base64 = base64.b64encode(file_bytes).decode()

        if file_base64 and not file_bytes:
            file_bytes = base64.b64decode(file_base64)

        return cls(
            file_path=data.get("file_path"),
            file_bytes=file_bytes,
            file_base64=file_base64,
        )
