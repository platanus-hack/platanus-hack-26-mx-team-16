"""List the per-phase execution timeline of a processing job, tenant-scoped."""

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.processing import JobNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.workflow_phase_execution import WorkflowPhaseExecution
from src.workflows.domain.repositories.workflow_phase_execution_repository import (
    WorkflowPhaseExecutionRepository,
)
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)


@dataclass
class WorkflowPhaseExecutionLister(UseCase):
    processing_job_id: UUID
    workflow_id: UUID
    tenant_id: UUID
    processing_job_repository: WorkflowProcessingJobRepository
    phase_execution_repository: WorkflowPhaseExecutionRepository

    async def execute(self) -> list[WorkflowPhaseExecution]:
        # Guard via the parent job: it pins both tenant and workflow, so a leaked
        # job id from another tenant/workflow 404s instead of exposing phases.
        job = await self.processing_job_repository.find_by_uuid(self.processing_job_id)
        if job is None or job.tenant_id != self.tenant_id or job.workflow_id != self.workflow_id:
            raise JobNotFoundError(str(self.processing_job_id))
        return await self.phase_execution_repository.list_by_job(self.processing_job_id)
