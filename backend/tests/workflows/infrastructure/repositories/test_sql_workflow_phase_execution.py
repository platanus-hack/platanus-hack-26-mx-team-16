from datetime import UTC, datetime
from uuid import uuid4

from expects import be_none, equal, expect, have_length

from src.common.domain.enums.pipelines import PhaseExecutionStatus
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob

_T0 = datetime(2026, 6, 16, 12, 0, 0, tzinfo=UTC)
_T1 = datetime(2026, 6, 16, 12, 0, 5, tzinfo=UTC)


async def _make_job(processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm):
    return await processing_job_repo.create(
        WorkflowProcessingJob(
            uuid=uuid4(),
            temporal_workflow_id=f"CASE#{case_orm.uuid.hex}_FILE#{file_orm.uuid.hex}",
            tenant_id=tenant_orm.uuid,
            workflow_id=workflow_orm.uuid,
            workflow_case_id=case_orm.uuid,
            file_id=file_orm.uuid,
        )
    )


async def test_record_started_then_finished__closes_single_row(
    phase_execution_repo, processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    job = await _make_job(processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm)

    await phase_execution_repo.record_started(
        processing_job_id=job.uuid,
        tenant_id=tenant_orm.uuid,
        seq=0,
        phase_id="extract_text",
        phase_kind="extract_text",
        started_at=_T0,
    )
    await phase_execution_repo.record_finished(
        processing_job_id=job.uuid,
        tenant_id=tenant_orm.uuid,
        seq=0,
        phase_id="extract_text",
        phase_kind="extract_text",
        status=PhaseExecutionStatus.COMPLETED,
        started_at=_T0,
        finished_at=_T1,
        output_snapshot={"key": "extract_text", "value": {"output_uri": "s3://x"}},
        error=None,
    )

    rows = await phase_execution_repo.list_by_job(job.uuid)

    expect(rows).to(have_length(1))
    expect(rows[0].status).to(equal(PhaseExecutionStatus.COMPLETED))
    expect(rows[0].output_snapshot).to(equal({"key": "extract_text", "value": {"output_uri": "s3://x"}}))
    expect(rows[0].duration_ms).to(equal(5000))


async def test_record_started__idempotent_on_job_seq(
    phase_execution_repo, processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    job = await _make_job(processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm)

    # Simulates Temporal at-least-once: the "started" activity runs twice.
    for _ in range(2):
        await phase_execution_repo.record_started(
            processing_job_id=job.uuid,
            tenant_id=tenant_orm.uuid,
            seq=0,
            phase_id="ingest",
            phase_kind="ingest",
            started_at=_T0,
        )

    rows = await phase_execution_repo.list_by_job(job.uuid)
    expect(rows).to(have_length(1))
    expect(rows[0].status).to(equal(PhaseExecutionStatus.RUNNING))


async def test_record_finished__upserts_when_started_was_missed(
    phase_execution_repo, processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    job = await _make_job(processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm)

    # No prior "started": the finish must still create a complete row.
    await phase_execution_repo.record_finished(
        processing_job_id=job.uuid,
        tenant_id=tenant_orm.uuid,
        seq=3,
        phase_id="finalize",
        phase_kind="finalize",
        status=PhaseExecutionStatus.FAILED,
        started_at=None,
        finished_at=_T1,
        output_snapshot=None,
        error={"message": "boom"},
    )

    rows = await phase_execution_repo.list_by_job(job.uuid)
    expect(rows).to(have_length(1))
    expect(rows[0].status).to(equal(PhaseExecutionStatus.FAILED))
    expect(rows[0].error).to(equal({"message": "boom"}))
    expect(rows[0].output_snapshot).to(be_none)


async def test_list_by_job__ordered_by_seq(
    phase_execution_repo, processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    job = await _make_job(processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm)

    for seq, kind in ((2, "classify_pages"), (0, "ingest"), (1, "extract_text")):
        await phase_execution_repo.record_started(
            processing_job_id=job.uuid,
            tenant_id=tenant_orm.uuid,
            seq=seq,
            phase_id=kind,
            phase_kind=kind,
            started_at=_T0,
        )

    rows = await phase_execution_repo.list_by_job(job.uuid)

    expect([r.seq for r in rows]).to(equal([0, 1, 2]))
    expect([r.phase_kind for r in rows]).to(equal(["ingest", "extract_text", "classify_pages"]))
