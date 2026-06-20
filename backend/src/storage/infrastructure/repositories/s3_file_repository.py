"""S3 + SQLAlchemy implementation of FileRepository."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.processing.file_upload import DocumentORM
from src.common.infrastructure.helpers.database import atomic_transaction
from src.common.settings import settings
from src.common.domain.models.file_upload import Document
from src.common.domain.exceptions.storage import FileNotFoundError
from src.storage.domain.repositories.file_repository import FileRepository
from src.storage.infrastructure.builders.file_upload_builder import build_file_upload
from src.storage.infrastructure.s3_client import get_s3_client


class S3FileRepository(FileRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, document: Document) -> Document:
        async with atomic_transaction(self.session):
            orm_instance = DocumentORM(
                uuid=document.uuid,
                tenant_id=document.tenant_id,
                file_name=document.file_name,
                mime=document.mime,
                size=document.size,
                s3_key=document.s3_key,
            )
            self.session.add(orm_instance)
            await self.session.flush()
            await self.session.refresh(orm_instance)
        return build_file_upload(orm_instance)

    async def find_by_id(self, file_id: UUID, tenant_id: UUID) -> Document | None:
        stmt = select(DocumentORM).where(
            DocumentORM.uuid == file_id,
            DocumentORM.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        orm_instance = result.scalar_one_or_none()
        if orm_instance is None:
            return None
        return build_file_upload(orm_instance)

    async def delete(self, file_id: UUID, tenant_id: UUID) -> None:
        async with atomic_transaction(self.session):
            stmt = select(DocumentORM).where(
                DocumentORM.uuid == file_id,
                DocumentORM.tenant_id == tenant_id,
            )
            result = await self.session.execute(stmt)
            try:
                orm_instance = result.scalar_one()
            except NoResultFound:
                raise FileNotFoundError(str(file_id))

            await self.session.delete(orm_instance)
            await self.session.flush()

    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": s3_key,
            },
            ExpiresIn=expires_in,
        )
        if settings.AWS_S3_PUBLIC_URL and settings.AWS_S3_ENDPOINT_URL:
            url = url.replace(settings.AWS_S3_ENDPOINT_URL, settings.AWS_S3_PUBLIC_URL, 1)
        return url
