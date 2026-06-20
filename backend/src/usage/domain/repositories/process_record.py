from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.common.domain.entities.common.pagination import Page
from src.usage.domain.models.process_record import ProcessRecord


class ProcessRecordRepository(ABC):
    @abstractmethod
    async def create(self, record: ProcessRecord) -> ProcessRecord:
        raise NotImplementedError

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: UUID,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 25,
        cursor: str | None = None,
    ) -> Page[ProcessRecord]:
        raise NotImplementedError

    @abstractmethod
    async def count_pages_by_tenant(
        self,
        tenant_id: UUID,
        from_dt: datetime,
        to_dt: datetime,
    ) -> int:
        raise NotImplementedError
