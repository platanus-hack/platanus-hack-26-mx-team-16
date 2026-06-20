from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.models.file_upload import Document


class FileRepository(ABC):
    @abstractmethod
    async def save(self, document: Document) -> Document:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, file_id: UUID, tenant_id: UUID) -> Document | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, file_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError
