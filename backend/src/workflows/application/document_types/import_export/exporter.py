"""Serialize a workflow's document types to a portable list (E6 · W4).

The E2 doc-type import was frontend-only; this is the backend counterpart that
mirrors :class:`WorkflowRulesExporter`. Each entry carries the natural shape the
FE import parser already accepts (``name``/``slug``/``fields``/``validation_rules``
…) so a single doc-type JSON stays valid on its own, and the bundle exporter can
nest the whole list.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.workflows.domain.repositories.document_type import DocumentTypeRepository

EXPORT_SCHEMA_VERSION = "1.0"


@dataclass
class WorkflowDocumentTypesExporter(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    document_type_repository: DocumentTypeRepository

    async def execute(self) -> list[dict[str, Any]]:
        doc_types = await self.document_type_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        return [self._serialize(dt) for dt in doc_types]

    @staticmethod
    def _serialize(dt: Any) -> dict[str, Any]:
        return {
            "name": dt.name,
            "slug": dt.slug,
            "description": dt.description,
            "keywords": list(dt.keywords or []),
            "examples": list(dt.examples or []),
            "fields": dt.fields,
            "validation_rules": list(dt.validation_rules or []),
            # Versión sellada actual (informativa; el import siempre versiona en
            # destino — append-only, nunca confía en el número entrante).
            "version": dt.current_version,
        }
