from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.workflows.domain.repositories.workflow import WorkflowRepository


@dataclass
class WorkflowDeleter(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    workflow_repository: WorkflowRepository

    async def execute(self) -> None:
        await self.workflow_repository.delete(self.workflow_id, self.tenant_id)
