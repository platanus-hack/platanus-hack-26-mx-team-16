"""Delete a WorkflowProcessingJob (children documents stay; FK is SET NULL)."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)


@dataclass
class WorkflowProcessingJobDeleter(UseCase):
    processing_job_id: UUID
    tenant_id: UUID
    processing_job_repository: WorkflowProcessingJobRepository

    async def execute(self) -> None:
        await self.processing_job_repository.delete(self.processing_job_id, self.tenant_id)
