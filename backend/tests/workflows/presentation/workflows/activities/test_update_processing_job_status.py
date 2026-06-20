from uuid import uuid4

import pytest
from expects import equal, expect
from sqlalchemy import delete, select

from src.common.database.config import get_database_config
from src.common.database.models.workflow_processing_job import WorkflowProcessingJobORM
from src.common.domain.enums.processing_job_events import JobStatus, JobStep
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    UpdateWorkflowProcessingJobStatusInput,
)
from src.workflows.presentation.workflows.activities.update_processing_job_status import (
    UpdateWorkflowProcessingJobStatusActivity,
)


@pytest.fixture
def session_maker():
    return get_database_config().session_maker


@pytest.fixture
def activity(session_maker):
    return UpdateWorkflowProcessingJobStatusActivity(session_maker=session_maker)


async def _seed_processing_job(async_session, tenant_orm, workflow_orm, case_orm, file_orm) -> WorkflowProcessingJobORM:
    """Seeds via the test session, commits so a separate activity-side session can see it."""
    orm = WorkflowProcessingJobORM(
        uuid=uuid4(),
        temporal_workflow_id=f"CASE#{case_orm.uuid.hex}_FILE#{file_orm.uuid.hex}",
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        workflow_case_id=case_orm.uuid,
        file_id=file_orm.uuid,
        last_seq=0,
    )
    async_session.add(orm)
    await async_session.commit()
    return orm


async def _cleanup_processing_job(session_maker, processing_job_uuid) -> None:
    """Wipe committed seed rows so subsequent tests see an empty table."""
    async with session_maker() as cleanup:
        await cleanup.execute(delete(WorkflowProcessingJobORM).where(WorkflowProcessingJobORM.uuid == processing_job_uuid))
        await cleanup.commit()


async def _read_processing_job(session_maker, processing_job_uuid) -> WorkflowProcessingJobORM:
    async with session_maker() as fresh:
        return (
            await fresh.execute(select(WorkflowProcessingJobORM).where(WorkflowProcessingJobORM.uuid == processing_job_uuid))
        ).scalar_one()


async def test_update__advances_status_step_and_seq(
    activity, async_session, session_maker, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = await _seed_processing_job(async_session, tenant_orm, workflow_orm, case_orm, file_orm)

    try:
        await activity.update_workflow_processing_job_status(
            UpdateWorkflowProcessingJobStatusInput(
                processing_job_uuid=processing_job.uuid,
                status=JobStatus.PROCESSING,
                current_step=JobStep.EXTRACT_TEXT,
                last_seq=3,
            )
        )

        refreshed = await _read_processing_job(session_maker, processing_job.uuid)

        expect(refreshed.status).to(equal(JobStatus.PROCESSING.value))
        expect(refreshed.current_step).to(equal(JobStep.EXTRACT_TEXT.value))
        expect(refreshed.last_seq).to(equal(3))
    finally:
        await _cleanup_processing_job(session_maker, processing_job.uuid)


async def test_update__idempotent_when_seq_not_advancing(
    activity, async_session, session_maker, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = await _seed_processing_job(async_session, tenant_orm, workflow_orm, case_orm, file_orm)

    try:
        await activity.update_workflow_processing_job_status(
            UpdateWorkflowProcessingJobStatusInput(
                processing_job_uuid=processing_job.uuid,
                status=JobStatus.PROCESSING,
                current_step=JobStep.EXTRACT_TEXT,
                last_seq=5,
            )
        )

        # Replayed activity at a stale seq must not regress the row.
        await activity.update_workflow_processing_job_status(
            UpdateWorkflowProcessingJobStatusInput(
                processing_job_uuid=processing_job.uuid,
                status=JobStatus.PENDING,
                current_step=JobStep.CLASSIFY_PAGES,
                last_seq=3,
            )
        )

        refreshed = await _read_processing_job(session_maker, processing_job.uuid)

        expect(refreshed.last_seq).to(equal(5))
        expect(refreshed.status).to(equal(JobStatus.PROCESSING.value))
        expect(refreshed.current_step).to(equal(JobStep.EXTRACT_TEXT.value))
    finally:
        await _cleanup_processing_job(session_maker, processing_job.uuid)


async def test_update__writes_error_payload_on_failed(
    activity, async_session, session_maker, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = await _seed_processing_job(async_session, tenant_orm, workflow_orm, case_orm, file_orm)

    try:
        await activity.update_workflow_processing_job_status(
            UpdateWorkflowProcessingJobStatusInput(
                processing_job_uuid=processing_job.uuid,
                status=JobStatus.FAILED,
                current_step=JobStep.VALIDATE,
                last_seq=9,
                error={"type": "RuntimeError", "message": "boom"},
            )
        )

        refreshed = await _read_processing_job(session_maker, processing_job.uuid)

        expect(refreshed.status).to(equal(JobStatus.FAILED.value))
        expect("boom" in (refreshed.error or "")).to(equal(True))
    finally:
        await _cleanup_processing_job(session_maker, processing_job.uuid)


async def test_update__persists_artifact_keys_independently(
    activity, async_session, session_maker, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = await _seed_processing_job(async_session, tenant_orm, workflow_orm, case_orm, file_orm)

    try:
        # Step 1 ack: extract_text artifact written, classified_pages stays NULL.
        await activity.update_workflow_processing_job_status(
            UpdateWorkflowProcessingJobStatusInput(
                processing_job_uuid=processing_job.uuid,
                status=JobStatus.PROCESSING,
                current_step=JobStep.EXTRACT_TEXT,
                last_seq=1,
                extracted_text_key="tenants/x/jobs/abc/extract_text.json",
            )
        )

        after_step1 = await _read_processing_job(session_maker, processing_job.uuid)
        expect(after_step1.extracted_text).to(equal("tenants/x/jobs/abc/extract_text.json"))
        expect(after_step1.classified_pages).to(equal(None))

        # Step 2 ack: classified_pages written, extract_text stays untouched.
        await activity.update_workflow_processing_job_status(
            UpdateWorkflowProcessingJobStatusInput(
                processing_job_uuid=processing_job.uuid,
                status=JobStatus.PROCESSING,
                current_step=JobStep.CLASSIFY_PAGES,
                last_seq=2,
                classified_pages_key="tenants/x/jobs/abc/classify_pages.json",
            )
        )

        after_step2 = await _read_processing_job(session_maker, processing_job.uuid)
        expect(after_step2.extracted_text).to(equal("tenants/x/jobs/abc/extract_text.json"))
        expect(after_step2.classified_pages).to(equal("tenants/x/jobs/abc/classify_pages.json"))
    finally:
        await _cleanup_processing_job(session_maker, processing_job.uuid)
