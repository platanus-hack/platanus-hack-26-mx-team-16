"""Sentinel "Otros" document type used to bucket workflow_documents that
were classified outside the doctypes configured in their workflow."""

from uuid import UUID

from src.common.domain.models.processing.document_type import DocumentType
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.processing.workflow_document_group import (
    WorkflowDocumentGroup,
)

OTHERS_DOCUMENT_TYPE_UUID = UUID("00000000-0000-0000-0000-000000000000")
OTHERS_DOCUMENT_TYPE_NAME = "Otros"
OTHERS_DOCUMENT_TYPE_DESCRIPTION = "Documentos clasificados fuera de los tipos configurados"


def build_others_document_type(tenant_id: UUID, workflow_id: UUID) -> DocumentType:
    return DocumentType(
        uuid=OTHERS_DOCUMENT_TYPE_UUID,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name=OTHERS_DOCUMENT_TYPE_NAME,
        description=OTHERS_DOCUMENT_TYPE_DESCRIPTION,
        is_shareable=False,
        validation_rules=[],
    )


def build_document_groups(
    document_types: list[DocumentType],
    documents: list[WorkflowDocument],
    tenant_id: UUID,
    workflow_id: UUID,
) -> list[WorkflowDocumentGroup]:
    """Group workflow documents by their document_type_id, always emitting one
    group per configured DocumentType (even when empty). Documents whose
    document_type_id is null OR points at a doctype not configured in this
    workflow are bucketed into a synthetic "Otros" group, which is appended
    only when at least one such document exists."""

    by_type_id: dict[UUID, list[WorkflowDocument]] = {dt.uuid: [] for dt in document_types}
    others: list[WorkflowDocument] = []

    for doc in documents:
        if doc.document_type_id is not None and doc.document_type_id in by_type_id:
            by_type_id[doc.document_type_id].append(doc)
        else:
            others.append(doc)

    groups: list[WorkflowDocumentGroup] = [
        WorkflowDocumentGroup(document_type=dt, documents=by_type_id[dt.uuid]) for dt in document_types
    ]

    if others:
        groups.append(
            WorkflowDocumentGroup(
                document_type=build_others_document_type(tenant_id, workflow_id),
                documents=others,
            )
        )

    return groups
