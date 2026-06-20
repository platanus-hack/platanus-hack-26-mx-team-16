from dataclasses import dataclass
from typing import Any, Self
from uuid import UUID

from src.common.domain.buses.commands import Command


@dataclass
class ExtractDocumentTypeSampleTextCommand(Command):
    document_type_id: UUID
    tenant_id: UUID

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type_id": str(self.document_type_id),
            "tenant_id": str(self.tenant_id),
        }

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(
            document_type_id=UUID(kwargs["document_type_id"]),
            tenant_id=UUID(kwargs["tenant_id"]),
        )


@dataclass
class SuggestDocumentTypeFieldsCommand(Command):
    document_type_id: UUID
    tenant_id: UUID
    prompt: str | None = None

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "document_type_id": str(self.document_type_id),
            "tenant_id": str(self.tenant_id),
            "prompt": self.prompt,
        }

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(
            document_type_id=UUID(kwargs["document_type_id"]),
            tenant_id=UUID(kwargs["tenant_id"]),
            prompt=kwargs.get("prompt"),
        )
