from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.common.domain.entities.common.pagination import Page
from src.common.domain.interfaces.use_case import UseCase
from src.usage.domain.models.process_record import ProcessRecord
from src.usage.domain.repositories.process_record import ProcessRecordRepository


@dataclass
class ListProcessRecords(UseCase):
    tenant_id: UUID
    process_record_repository: ProcessRecordRepository
    from_dt: datetime | None = None
    to_dt: datetime | None = None
    limit: int = 25
    cursor: str | None = None

    async def execute(self) -> Page[ProcessRecord]:
        return await self.process_record_repository.list_by_tenant(
            tenant_id=self.tenant_id,
            from_dt=self.from_dt,
            to_dt=self.to_dt,
            limit=self.limit,
            cursor=self.cursor,
        )
