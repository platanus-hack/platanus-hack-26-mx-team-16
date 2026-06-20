from src.common.database.models.knowledge_base.kb_document import KBDocumentORM
from src.common.domain.models.knowledge_base.kb_document import KBDocument
from src.common.domain.enums.knowledge_base import KBDocumentStatus


def build_kb_document(orm_instance: KBDocumentORM) -> KBDocument:
    return KBDocument(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        file_name=orm_instance.file_name,
        slug=orm_instance.slug,
        mime=orm_instance.mime,
        file_id=orm_instance.file_id,
        workflow_id=orm_instance.workflow_id,
        extracted_text=orm_instance.extracted_text,
        status=KBDocumentStatus.from_value(orm_instance.status, default=KBDocumentStatus.VECTORIZING),
        chunk_count=orm_instance.chunk_count or 0,
        error_message=orm_instance.error_message,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
