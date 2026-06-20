"""CreateVirtualDocument — "todo dato es un documento" (E3 · plan §4.1.3).

Materializa datos sin archivo como ``WorkflowDocument``:
- ``EXTERNAL_DATA``: payload validado que inyecta el cliente vía
  ``POST /v1/cases/{id}/data`` (Caso 1B).
- ``TOOL``: resultado de una tool HTTP de la fase ``enrich`` (``@poliza``).

El documento nace EXTRACTED/completed con ``extraction = mapped_extraction =
payload`` (plano), así el motor de reglas (``@slug.path``), la proyección
x-source y la síntesis lo consumen SIN cambios — la resolución matchea por
``document_type_slug``, por eso el ``doc_type_slug`` es OBLIGATORIO y debe
existir en el catálogo del workflow (sin creación on-the-fly: el admin define
"datos_validados"/"poliza" una vez). ``field_confidence`` queda en None: los
datos vienen validados por el cliente/tool y el confidence_gate no debe
flaggearlos.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.common.domain.enums.workflows import (
    WorkflowDocumentSource,
    WorkflowDocumentStatus,
)
from src.common.domain.exceptions.processing import DocumentTypeNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository

VIRTUAL_SOURCES = (WorkflowDocumentSource.EXTERNAL_DATA, WorkflowDocumentSource.TOOL)


@dataclass
class CreateVirtualDocument(UseCase):
    tenant_id: UUID
    workflow_id: UUID
    case_id: UUID
    doc_type_slug: str
    payload: dict
    source: WorkflowDocumentSource
    document_repository: WorkflowDocumentRepository
    document_type_repository: DocumentTypeRepository
    file_name: str | None = None

    async def execute(self) -> WorkflowDocument:
        if self.source not in VIRTUAL_SOURCES:
            msg = f"source {self.source} is not a virtual document source"
            raise ValueError(msg)

        doc_types = await self.document_type_repository.list_by_workflow(
            self.workflow_id, self.tenant_id
        )
        doc_type = next((d for d in doc_types if d.slug == self.doc_type_slug), None)
        if doc_type is None:
            raise DocumentTypeNotFoundError(self.doc_type_slug)

        document = WorkflowDocument(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            case_id=self.case_id,
            document_type_id=doc_type.uuid,
            file_name=self.file_name or f"{self.doc_type_slug}.json",
            status=WorkflowDocumentStatus.EXTRACTED,
            source=self.source,
            extraction=self.payload,
            mapped_extraction=self.payload,
            processing_status="completed",
            # D6': sella la versión vigente del schema del doc type.
            document_type_version=doc_type.current_version,
        )
        return await self.document_repository.create(document)
