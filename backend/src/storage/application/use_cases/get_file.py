from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.file_upload import Document
from src.common.domain.exceptions.storage import FileNotFoundError
from src.storage.domain.repositories.file_repository import FileRepository


@dataclass
class GetFile(UseCase):
    file_id: UUID
    tenant_id: UUID
    file_repository: FileRepository

    async def execute(self) -> dict:
        file_upload = await self.file_repository.find_by_id(self.file_id, self.tenant_id)
        if not file_upload:
            raise FileNotFoundError(str(self.file_id))

        presigned_url = self.file_repository.get_presigned_url(file_upload.s3_key)

        return {
            "file": file_upload,
            "presigned_url": presigned_url,
        }
