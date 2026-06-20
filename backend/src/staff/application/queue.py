"""Cola L1 unificada cross-tenant (ADR 0001, alcance 1)."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.staff.domain.entities import StaffQueueItem
from src.staff.domain.repositories.staff_human_task import StaffHumanTaskRepository


@dataclass
class ListL1Queue(UseCase):
    repository: StaffHumanTaskRepository
    tenant_id: UUID | None = None
    status: str | None = "pending"
    limit: int = 200
    # E6 §3: "approval" | "qa" | None (ambos) — segmenta la cola staff.
    kind: str | None = None

    async def execute(self) -> list[StaffQueueItem]:
        return await self.repository.list_open_l1(
            tenant_id=self.tenant_id,
            status=self.status,
            limit=self.limit,
            kind=self.kind,
        )
