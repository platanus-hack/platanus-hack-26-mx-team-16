from src.common.database.models.document_type import (
    DocumentTypeORM,
    DocumentTypeVersionORM,
)
from src.common.domain.models.processing.document_type import (
    DocumentType,
    DocumentTypeVersion,
)


def build_document_type(orm: DocumentTypeORM) -> DocumentType:
    return DocumentType(
        uuid=orm.uuid,
        tenant_id=orm.tenant_id,
        workflow_id=orm.workflow_id,
        name=orm.name,
        is_shareable=orm.is_shareable,
        slug=orm.slug,
        description=orm.description,
        fields=orm.fields,
        keywords=orm.keywords,
        examples=orm.examples,
        validation_rules=orm.validation_rules,
        sample_file_id=orm.sample_file_id,
        sample_file_text=orm.sample_file_text,
        current_version=orm.current_version,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def build_document_type_version(orm: DocumentTypeVersionORM) -> DocumentTypeVersion:
    return DocumentTypeVersion(
        uuid=orm.uuid,
        document_type_id=orm.document_type_id,
        version=orm.version,
        fields=orm.fields,
        validation_rules=orm.validation_rules,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
