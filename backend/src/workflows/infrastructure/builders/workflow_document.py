from src.common.domain.enums.workflows import WorkflowDocumentStatus, WorkflowDocumentSource
from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.common.domain.models.processing.workflow_document import WorkflowDocument


def build_workflow_document(orm_instance: WorkflowDocumentORM) -> WorkflowDocument:
    return WorkflowDocument(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        workflow_id=orm_instance.workflow_id,
        case_id=orm_instance.workflow_case_id,
        document_type_id=orm_instance.document_type_id,
        file_name=orm_instance.name,
        file_id=orm_instance.document_id,
        status=WorkflowDocumentStatus.from_value(orm_instance.status),
        source=WorkflowDocumentSource.from_value(orm_instance.source),
        extraction=orm_instance.extraction,
        mapped_extraction=orm_instance.mapped_extraction,
        field_confidence=orm_instance.field_confidence,
        needs_clarification=orm_instance.needs_clarification,
        extraction_pages=orm_instance.extraction_pages,
        validation=orm_instance.validation,
        extracted_text=orm_instance.extracted_text,
        extraction_metadata=orm_instance.extraction_metadata,
        processing_job_id=orm_instance.processing_job_id,
        document_index=orm_instance.document_index,
        page_range=orm_instance.page_range,
        processing_status=orm_instance.processing_status,
        output=orm_instance.output,
        output_provenance=orm_instance.output_provenance,
        document_type_version=orm_instance.document_type_version,
        extract_confidence=orm_instance.extract_confidence,
        signals=orm_instance.signals,
        verification=orm_instance.verification,
        parent_document_id=orm_instance.parent_document_id,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
