from src.common.database.models.processing.file_upload import DocumentORM
from src.common.domain.models.file_upload import Document


def build_file_upload(orm_instance: DocumentORM) -> Document:
    return Document(
        uuid=orm_instance.uuid,
        tenant_id=orm_instance.tenant_id,
        file_name=orm_instance.file_name,
        mime=orm_instance.mime,
        size=orm_instance.size,
        s3_key=orm_instance.s3_key,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
