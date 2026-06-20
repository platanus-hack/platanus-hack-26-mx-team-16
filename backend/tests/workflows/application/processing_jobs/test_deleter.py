from uuid import uuid4

from src.workflows.application.processing_jobs.deleter import (
    WorkflowProcessingJobDeleter,
)


async def test_execute__delegates_to_repository_with_id_and_tenant(tenant_id, processing_job_repository):
    processing_job_id = uuid4()

    use_case = WorkflowProcessingJobDeleter(
        processing_job_id=processing_job_id,
        tenant_id=tenant_id,
        processing_job_repository=processing_job_repository,
    )

    await use_case.execute()

    processing_job_repository.delete.assert_called_once_with(processing_job_id, tenant_id)
