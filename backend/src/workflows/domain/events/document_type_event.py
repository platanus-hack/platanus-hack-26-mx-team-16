from __future__ import annotations

from typing import Literal
from uuid import UUID

from src.common.domain.events.base import Event

DocumentTypeEventType = Literal[
    "SAMPLE_TEXT_EXTRACTING",
    "SAMPLE_TEXT_EXTRACTED",
    "SAMPLE_TEXT_FAILED",
    "FIELDS_SUGGESTING",
    "FIELDS_SUGGESTED",
    "FIELDS_SUGGESTION_FAILED",
]

DOCTYPE_TERMINAL_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "SAMPLE_TEXT_EXTRACTED",
        "SAMPLE_TEXT_FAILED",
        "FIELDS_SUGGESTED",
        "FIELDS_SUGGESTION_FAILED",
    }
)


def channel_for_doctype(doctype_id: UUID) -> str:
    return f"document_type:{doctype_id.hex}"


class DocumentTypeEvent(Event):
    type: DocumentTypeEventType
    document_type_id: UUID

    @property
    def channel(self) -> str:
        return channel_for_doctype(self.document_type_id)
