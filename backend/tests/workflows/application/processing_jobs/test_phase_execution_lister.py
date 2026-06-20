from uuid import uuid4

import pytest
from expects import equal, expect, have_length

from src.common.domain.exceptions.processing import JobNotFoundError
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.application.processing_jobs.phase_execution_lister import (
    WorkflowPhaseExecutionLister,
)

_TENANT = uuid4()
_WORKFLOW = uuid4()
_JOB = uuid4()


def _job(tenant_id=_TENANT, workflow_id=_WORKFLOW) -> WorkflowProcessingJob:
    return WorkflowProcessingJob(
        uuid=_JOB,
        temporal_workflow_id="CASE#x_FILE#y",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        file_id=uuid4(),
    )


class _FakeJobRepo:
    def __init__(self, job):
        self._job = job

    async def find_by_uuid(self, uuid):  # noqa: ANN001
        return self._job


class _FakePhaseRepo:
    def __init__(self, rows):
        self._rows = rows

    async def list_by_job(self, processing_job_id):  # noqa: ANN001
        return self._rows


def _lister(job, rows):
    return WorkflowPhaseExecutionLister(
        processing_job_id=_JOB,
        workflow_id=_WORKFLOW,
        tenant_id=_TENANT,
        processing_job_repository=_FakeJobRepo(job),
        phase_execution_repository=_FakePhaseRepo(rows),
    )


async def test_execute__returns_phase_rows_for_owned_job():
    result = await _lister(_job(), ["row-1", "row-2"]).execute()

    expect(result).to(have_length(2))
    expect(result).to(equal(["row-1", "row-2"]))


async def test_execute__missing_job_raises_not_found():
    with pytest.raises(JobNotFoundError):
        await _lister(None, []).execute()


async def test_execute__other_tenant_raises_not_found():
    with pytest.raises(JobNotFoundError):
        await _lister(_job(tenant_id=uuid4()), ["leak"]).execute()


async def test_execute__other_workflow_raises_not_found():
    with pytest.raises(JobNotFoundError):
        await _lister(_job(workflow_id=uuid4()), ["leak"]).execute()
