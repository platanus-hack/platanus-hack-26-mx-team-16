"""Fetch a single WorkflowProcessingJob by uuid, scoped to tenant."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.processing import JobNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)


@dataclass
class WorkflowProcessingJobGetter(UseCase):
    processing_job_id: UUID
    tenant_id: UUID
    processing_job_repository: WorkflowProcessingJobRepository

    async def execute(self) -> WorkflowProcessingJob:
        processing_job = await self.processing_job_repository.find_by_uuid(self.processing_job_id)
        if processing_job is None or processing_job.tenant_id != self.tenant_id:
            raise JobNotFoundError(str(self.processing_job_id))
        return processing_job
