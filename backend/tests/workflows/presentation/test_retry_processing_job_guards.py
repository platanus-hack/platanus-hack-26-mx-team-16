"""Re-IA 2026-06 · guards del endpoint POST …/jobs/{id}/retry.

El handler es un wrapper fino sobre el dispatcher (que ya permite re-dispatch
implícito SOLO en FAILED). Aquí se prueban los guards previos: 404 si el job
no existe o no pertenece al tenant/workflow del path; 409 si no está FAILED.
El happy path (re-dispatch real) lo cubren la suite del dispatcher y el E2E.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import uuid4

from expects import equal, expect

from src.common.domain.enums.workflows import WorkflowProcessingJobStatus
from src.workflows.presentation.endpoints.workflow_processing_jobs import (
    retry_processing_job,
)

_TENANT = uuid4()
_WORKFLOW = uuid4()


class _FakeJobRepo:
    def __init__(self, job):
        self.job = job

    async def find_by_uuid(self, uuid):
        return self.job


def _deps(job):
    app_context = SimpleNamespace(
        domain=SimpleNamespace(processing_job_repository=_FakeJobRepo(job))
    )
    tenant = SimpleNamespace(uuid=_TENANT)
    user = SimpleNamespace(uuid=uuid4())
    return app_context, tenant, user


def _job(**overrides):
    base = dict(
        uuid=uuid4(),
        tenant_id=_TENANT,
        workflow_id=_WORKFLOW,
        file_id=uuid4(),
        workflow_case_id=uuid4(),
        status=WorkflowProcessingJobStatus.FAILED,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _payload(response) -> dict:
    # ApiJSONResponse envuelve el contenido no-error bajo {"data": ..., "timestamp": ...}.
    body = json.loads(response.body)
    return body.get("data", body)


async def test_retry__404_when_job_missing():
    app_context, tenant, user = _deps(job=None)

    response = await retry_processing_job(
        workflow_id=_WORKFLOW,
        processing_job_id=uuid4(),
        temporal_client=None,
        session=None,
        user=user,
        app_context=app_context,
        tenant=tenant,
    )

    expect(response.status_code).to(equal(404))
    expect(_payload(response)["error"]).to(equal("processing_job.not_found"))


async def test_retry__404_when_job_belongs_to_another_workflow():
    job = _job(workflow_id=uuid4())
    app_context, tenant, user = _deps(job)

    response = await retry_processing_job(
        workflow_id=_WORKFLOW,
        processing_job_id=job.uuid,
        temporal_client=None,
        session=None,
        user=user,
        app_context=app_context,
        tenant=tenant,
    )

    expect(response.status_code).to(equal(404))


async def test_retry__404_when_job_belongs_to_another_tenant():
    job = _job(tenant_id=uuid4())
    app_context, tenant, user = _deps(job)

    response = await retry_processing_job(
        workflow_id=_WORKFLOW,
        processing_job_id=job.uuid,
        temporal_client=None,
        session=None,
        user=user,
        app_context=app_context,
        tenant=tenant,
    )

    expect(response.status_code).to(equal(404))


async def test_retry__409_when_job_not_failed():
    job = _job(status=WorkflowProcessingJobStatus.COMPLETED)
    app_context, tenant, user = _deps(job)

    response = await retry_processing_job(
        workflow_id=_WORKFLOW,
        processing_job_id=job.uuid,
        temporal_client=None,
        session=None,
        user=user,
        app_context=app_context,
        tenant=tenant,
    )

    expect(response.status_code).to(equal(409))
    expect(_payload(response)["error"]).to(equal("processing_job.not_failed"))
