import base64
from dataclasses import dataclass
from typing import Any, Self
from uuid import UUID

from src.common.domain.buses.commands import Command


@dataclass
class VectorizeKBDocumentCommand(Command):
    document_id: UUID
    tenant_id: UUID
    file_name: str
    mime_type: str
    file_content: bytes

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": str(self.document_id),
            "tenant_id": str(self.tenant_id),
            "file_name": self.file_name,
            "mime_type": self.mime_type,
            "file_content": base64.b64encode(self.file_content).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(
            document_id=UUID(kwargs["document_id"]),
            tenant_id=UUID(kwargs["tenant_id"]),
            file_name=kwargs["file_name"],
            mime_type=kwargs["mime_type"],
            file_content=base64.b64decode(kwargs["file_content"]),
        )
