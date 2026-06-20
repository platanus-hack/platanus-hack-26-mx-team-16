from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.workflows import WorkflowDocumentSource, WorkflowDocumentStatus


class WorkflowDocument(BaseModel):
    uuid: UUID = Field(...)
    tenant_id: UUID = Field(...)
    workflow_id: UUID | None = Field(default=None)
    case_id: UUID | None = Field(default=None)
    document_type_id: UUID | None = Field(default=None)
    file_name: str | None = Field(default=None)
    file_id: UUID | None = Field(default=None)
    mime_type: str | None = Field(default=None)
    status: WorkflowDocumentStatus = Field(default=WorkflowDocumentStatus.EMPTY)
    source: WorkflowDocumentSource = Field(default=WorkflowDocumentSource.SINGLE)
    extraction: dict = Field(default_factory=dict)
    mapped_extraction: dict | None = Field(default=None)
    field_confidence: dict | None = Field(default=None)
    needs_clarification: list | None = Field(default=None)
    extraction_pages: list[int] | None = Field(default=None)
    validation: list = Field(default_factory=list)
    extracted_text: str | None = Field(default=None)
    extraction_metadata: dict = Field(default_factory=dict)
    processing_job_id: UUID | None = Field(default=None)
    document_index: int | None = Field(default=None)
    page_range: dict | None = Field(default=None)
    processing_status: str | None = Field(default=None)
    error: dict | None = Field(default=None)
    # E2 · spec case-output: output del caso acotado a este documento + provenance.
    output: dict | None = Field(default=None)
    output_provenance: dict | None = Field(default=None)
    # D6' · versión del schema del doc type sellada por el run que lo extrajo.
    document_type_version: int | None = Field(default=None)
    # E3 · capa-2 de confianza (fase assess): {campo: float} y
    # {campo: {signals: [...], explanation, candidates: [...]}}.
    extract_confidence: dict | None = Field(default=None)
    signals: dict | None = Field(default=None)
    # E5 · verificación por campo (Inspection Bench / revisión L1-L2):
    # {fieldPath: {value, verified_by, level, verified_at, previous_value}}.
    verification: dict | None = Field(default=None)
    # E5 · lineage doc→doc del fan-out: doc bulk original del SPLIT_CHILD.
    parent_document_id: UUID | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    @property
    def persist_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "workflow_id": self.workflow_id,
            "case_id": self.case_id,
            "document_type_id": self.document_type_id,
            "file_name": self.file_name,
            "file_id": self.file_id,
            "status": self.status,
            "source": self.source,
            "extraction": self.extraction,
            "mapped_extraction": self.mapped_extraction,
            "field_confidence": self.field_confidence,
            "needs_clarification": self.needs_clarification,
            "extraction_pages": self.extraction_pages,
            "validation": self.validation,
            "extracted_text": self.extracted_text,
            "extraction_metadata": self.extraction_metadata,
            "processing_job_id": self.processing_job_id,
            "document_index": self.document_index,
            "page_range": self.page_range,
            "processing_status": self.processing_status,
            "error": self.error,
            "output": self.output,
            "output_provenance": self.output_provenance,
            "document_type_version": self.document_type_version,
            "extract_confidence": self.extract_confidence,
            "signals": self.signals,
            "verification": self.verification,
            "parent_document_id": self.parent_document_id,
        }
