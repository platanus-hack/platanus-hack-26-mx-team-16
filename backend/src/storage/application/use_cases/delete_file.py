from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.exceptions.storage import FileNotFoundError
from src.storage.domain.repositories.file_repository import FileRepository
from src.storage.infrastructure.s3_client import get_s3_client
from src.common.settings import settings


@dataclass
class DeleteFile(UseCase):
    file_id: UUID
    tenant_id: UUID
    file_repository: FileRepository

    async def execute(self) -> None:
        file_upload = await self.file_repository.find_by_id(self.file_id, self.tenant_id)
        if not file_upload:
            raise FileNotFoundError(str(self.file_id))

        s3_client = get_s3_client()
        s3_client.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=file_upload.s3_key,
        )

        await self.file_repository.delete(self.file_id, self.tenant_id)
