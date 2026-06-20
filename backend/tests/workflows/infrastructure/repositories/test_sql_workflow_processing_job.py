import asyncio
from uuid import uuid4

import pytest
from expects import be_a, be_none, contain, equal, expect, have_length

from src.common.database.config import get_database_config
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.common.domain.enums.workflows import WorkflowProcessingJobStatus
from src.workflows.infrastructure.repositories.sql_workflow_processing_job import (
    SQLWorkflowProcessingJobRepository,
)


def _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm) -> WorkflowProcessingJob:
    return WorkflowProcessingJob(
        uuid=uuid4(),
        temporal_workflow_id=f"CASE#{case_orm.uuid.hex}_FILE#{file_orm.uuid.hex}",
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        workflow_case_id=case_orm.uuid,
        file_id=file_orm.uuid,
    )


async def test_create__persists_pending_with_attempts_zero(
    processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)

    result = await processing_job_repo.create(processing_job)

    expect(result).to(be_a(WorkflowProcessingJob))
    expect(result.uuid).to(equal(processing_job.uuid))
    expect(result.temporal_workflow_id).to(equal(processing_job.temporal_workflow_id))
    expect(result.status).to(equal(WorkflowProcessingJobStatus.PENDING))
    expect(result.attempts).to(equal(0))


async def test_find_by_uuid__returns_processing_job(processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm):
    processing_job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)

    found = await processing_job_repo.find_by_uuid(processing_job.uuid)

    expect(found).not_to(be_none)
    expect(found.uuid).to(equal(processing_job.uuid))


async def test_find_by_uuid__not_found_returns_none(processing_job_repo):
    found = await processing_job_repo.find_by_uuid(uuid4())

    expect(found).to(be_none)


async def test_find_by_temporal_workflow_id__returns_processing_job(
    processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)

    found = await processing_job_repo.find_by_temporal_workflow_id(processing_job.temporal_workflow_id)

    expect(found).not_to(be_none)
    expect(found.uuid).to(equal(processing_job.uuid))


async def test_claim__transitions_pending_to_running_and_increments_attempts(
    processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)

    claimed = await processing_job_repo.claim(processing_job.uuid)

    expect(claimed).not_to(be_none)
    expect(claimed.status).to(equal(WorkflowProcessingJobStatus.RUNNING))
    expect(claimed.attempts).to(equal(1))


async def test_claim__skips_done_processing_job(processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm):
    processing_job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)
    await processing_job_repo.mark_done(processing_job.uuid, summary={"documents_created": 0})

    claimed = await processing_job_repo.claim(processing_job.uuid)

    expect(claimed).to(be_none)


async def test_claim__skip_locked_only_one_concurrent_winner(
    async_session, tenant_orm, workflow_orm, case_orm, file_orm
):
    """Two concurrent transactions racing on the same row: SKIP LOCKED guarantees
    exactly one wins and the other gets None instead of blocking.

    Requires committed state so two SEPARATE sessions can see the row, hence
    the explicit cleanup at the end (other tests assume rollback isolation).
    """
    seed_repo = SQLWorkflowProcessingJobRepository(async_session)
    processing_job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    await seed_repo.create(processing_job)
    await async_session.commit()

    session_maker = get_database_config().session_maker

    async def claim_in_new_session() -> WorkflowProcessingJob | None:
        async with session_maker() as session:
            repo = SQLWorkflowProcessingJobRepository(session)
            result = await repo.claim(processing_job.uuid)
            if result is not None:
                # Hold the row briefly so the parallel transaction sees it locked
                await asyncio.sleep(0.05)
                await session.commit()
            else:
                await session.rollback()
            return result

    try:
        results = await asyncio.gather(
            claim_in_new_session(),
            claim_in_new_session(),
        )

        winners = [r for r in results if r is not None]
        losers = [r for r in results if r is None]

        expect(winners).to(have_length(1))
        expect(losers).to(have_length(1))
        expect(winners[0].status).to(equal(WorkflowProcessingJobStatus.RUNNING))
    finally:
        # Cleanup committed data so subsequent tests see an empty table.
        async with session_maker() as cleanup:
            from sqlalchemy import delete

            from src.common.database.models.workflow_processing_job import WorkflowProcessingJobORM

            await cleanup.execute(
                delete(WorkflowProcessingJobORM).where(WorkflowProcessingJobORM.uuid == processing_job.uuid)
            )
            await cleanup.commit()


async def test_mark_done__sets_status_and_summary(processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm):
    processing_job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)
    await processing_job_repo.claim(processing_job.uuid)  # PENDING → RUNNING (non-terminal)

    await processing_job_repo.mark_done(processing_job.uuid, summary={"documents_created": 3})

    final = await processing_job_repo.find_by_uuid(processing_job.uuid)
    expect(final.status).to(equal(WorkflowProcessingJobStatus.COMPLETED))
    expect(final.error).to(be_none)
    expect(final.result_summary).to(equal({"documents_created": 3}))


async def test_mark_done__refuses_to_overwrite_terminal_status(
    processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    """The atomic guard prevents `mark_done` from flipping an already-failed
    row to COMPLETED — once a document set is in a terminal state it stays
    there until an explicit `reset_to_pending` is called."""
    processing_job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)
    await processing_job_repo.mark_failed(processing_job.uuid, error="prior error")

    await processing_job_repo.mark_done(processing_job.uuid, summary={"documents_created": 3})

    final = await processing_job_repo.find_by_uuid(processing_job.uuid)
    expect(final.status).to(equal(WorkflowProcessingJobStatus.FAILED))
    expect(final.error).to(equal("prior error"))


async def test_mark_failed__refuses_to_overwrite_completed(
    processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    """Late `mark_failed` (e.g. runner timeout while the worker actually
    completed) must not flip a COMPLETED row to FAILED."""
    processing_job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)
    await processing_job_repo.claim(processing_job.uuid)
    await processing_job_repo.mark_done(processing_job.uuid, summary={"documents_created": 1})

    await processing_job_repo.mark_failed(processing_job.uuid, error="late timeout")

    final = await processing_job_repo.find_by_uuid(processing_job.uuid)
    expect(final.status).to(equal(WorkflowProcessingJobStatus.COMPLETED))
    expect(final.error).to(be_none)


async def test_mark_failed__sets_status_and_error(processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm):
    processing_job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)

    await processing_job_repo.mark_failed(processing_job.uuid, error="boom")

    final = await processing_job_repo.find_by_uuid(processing_job.uuid)
    expect(final.status).to(equal(WorkflowProcessingJobStatus.FAILED))
    expect(final.error).to(equal("boom"))


async def test_reset_to_pending__clears_error_and_sets_pending(
    processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    processing_job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)
    await processing_job_repo.mark_failed(processing_job.uuid, error="boom")

    await processing_job_repo.reset_to_pending(processing_job.uuid)

    final = await processing_job_repo.find_by_uuid(processing_job.uuid)
    expect(final.status).to(equal(WorkflowProcessingJobStatus.PENDING))
    expect(final.error).to(be_none)


async def test_list_unfinished__filters_to_pending_and_running(
    processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    pending = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    pending.temporal_workflow_id = f"pending-{uuid4().hex[:8]}"
    running = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    running.temporal_workflow_id = f"running-{uuid4().hex[:8]}"
    done = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    done.temporal_workflow_id = f"done-{uuid4().hex[:8]}"
    failed = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    failed.temporal_workflow_id = f"failed-{uuid4().hex[:8]}"

    await processing_job_repo.create(pending)
    await processing_job_repo.create(running)
    await processing_job_repo.claim(running.uuid)  # pending → running
    await processing_job_repo.create(done)
    await processing_job_repo.mark_done(done.uuid, summary=None)
    await processing_job_repo.create(failed)
    await processing_job_repo.mark_failed(failed.uuid, error="x")

    unfinished = await processing_job_repo.list_unfinished()

    returned_ids = {j.uuid for j in unfinished}
    expect(returned_ids).to(contain(pending.uuid))
    expect(returned_ids).to(contain(running.uuid))
    expect(returned_ids).not_to(contain(done.uuid))
    expect(returned_ids).not_to(contain(failed.uuid))


async def test_list_by_source_token__matches_prefix_and_enriches_file_name(
    processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    token = f"rt_{uuid4().hex[:10]}"
    mine = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    mine.temporal_workflow_id = f"SRC#{token}_FILE#{file_orm.uuid.hex[:12]}"
    other = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    other.temporal_workflow_id = f"SRC#rt_other_FILE#{uuid4().hex[:12]}"
    await processing_job_repo.create(mine)
    await processing_job_repo.create(other)

    rows = await processing_job_repo.list_by_source_token(token, tenant_orm.uuid)

    ids = {r.uuid for r in rows}
    expect(ids).to(contain(mine.uuid))
    expect(ids).not_to(contain(other.uuid))
    match = next(r for r in rows if r.uuid == mine.uuid)
    expect(match.file_name).to(equal(file_orm.file_name))


async def test_list_by_source_token__is_tenant_scoped(
    processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    token = f"rt_{uuid4().hex[:10]}"
    job = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    job.temporal_workflow_id = f"SRC#{token}_FILE#{uuid4().hex[:12]}"
    await processing_job_repo.create(job)

    rows = await processing_job_repo.list_by_source_token(token, uuid4())

    expect(rows).to(have_length(0))


async def test_list_by_source_token__escapes_like_wildcards_in_token(
    processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm
):
    # A literal underscore in the token must not act as a LIKE wildcard: a job
    # from a *different* source whose token differs only at that position
    # (``aXb`` vs ``a_b``) must not leak in. Guards the startswith(autoescape).
    other = _build_processing_job(tenant_orm, workflow_orm, case_orm, file_orm)
    other.temporal_workflow_id = f"SRC#aXb_FILE#{uuid4().hex[:12]}"
    await processing_job_repo.create(other)

    rows = await processing_job_repo.list_by_source_token("a_b", tenant_orm.uuid)

    expect(rows).to(have_length(0))


def _build_deletable_set(tenant_orm, workflow_orm, case_orm, file_orm) -> WorkflowProcessingJob:
    return WorkflowProcessingJob(
        uuid=uuid4(),
        temporal_workflow_id=f"JOB-{uuid4().hex[:12]}",
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        workflow_case_id=case_orm.uuid,
        file_id=file_orm.uuid,
    )


async def test_delete__removes_the_row(processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm):
    processing_job = _build_deletable_set(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)

    await processing_job_repo.delete(processing_job.uuid, tenant_orm.uuid)

    expect(await processing_job_repo.find_by_uuid(processing_job.uuid)).to(be_none)


async def test_delete__is_tenant_scoped(processing_job_repo, tenant_orm, workflow_orm, case_orm, file_orm):
    processing_job = _build_deletable_set(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)

    await processing_job_repo.delete(processing_job.uuid, uuid4())

    expect(await processing_job_repo.find_by_uuid(processing_job.uuid)).not_to(be_none)


async def test_delete__detaches_child_workflow_documents(
    processing_job_repo,
    async_session,
    tenant_orm,
    workflow_orm,
    case_orm,
    file_orm,
):
    """FK ON DELETE SET NULL: deleting the parent set leaves children intact
    with `processing_job_id` cleared. Verified through repository methods."""
    from src.common.domain.enums.workflows import (
        WorkflowDocumentSource,
        WorkflowDocumentStatus,
    )
    from src.common.domain.models.processing.workflow_document import WorkflowDocument
    from src.workflows.infrastructure.repositories.sql_document_repository import (
        SQLWorkflowDocumentRepository,
    )

    document_repo = SQLWorkflowDocumentRepository(async_session)
    processing_job = _build_deletable_set(tenant_orm, workflow_orm, case_orm, file_orm)
    await processing_job_repo.create(processing_job)
    child = await document_repo.create(
        WorkflowDocument(
            uuid=uuid4(),
            tenant_id=tenant_orm.uuid,
            workflow_id=workflow_orm.uuid,
            case_id=case_orm.uuid,
            file_id=file_orm.uuid,
            file_name="child.pdf",
            status=WorkflowDocumentStatus.EMPTY,
            source=WorkflowDocumentSource.SINGLE,
            processing_job_id=processing_job.uuid,
        )
    )

    await processing_job_repo.delete(processing_job.uuid, tenant_orm.uuid)
    refetched = await document_repo.find_by_id(child.uuid, tenant_orm.uuid)

    expect(refetched).not_to(be_none)
    expect(refetched.processing_job_id).to(be_none)


async def test_workflow_processing_job_deleter__commits_so_other_sessions_see_the_row_gone(
    async_session, tenant_orm, workflow_orm, case_orm, file_orm
):
    """Regression for the missing commit: the WorkflowProcessingJobDeleter use
    case runs inside a FastAPI request session that never commits on its
    own — the SQL repo MUST wrap delete() in atomic_transaction. We assert
    that by reading the row from a fully independent session through the
    repository's find_by_uuid (no raw SQL)."""
    from src.workflows.application.processing_jobs.deleter import (
        WorkflowProcessingJobDeleter,
    )

    seed_repo = SQLWorkflowProcessingJobRepository(async_session)
    processing_job = _build_deletable_set(tenant_orm, workflow_orm, case_orm, file_orm)
    await seed_repo.create(processing_job)
    await async_session.commit()

    session_maker = get_database_config().session_maker

    try:
        async with session_maker() as use_case_session:
            await WorkflowProcessingJobDeleter(
                processing_job_id=processing_job.uuid,
                tenant_id=tenant_orm.uuid,
                processing_job_repository=SQLWorkflowProcessingJobRepository(use_case_session),
            ).execute()

        async with session_maker() as verify_session:
            found = await SQLWorkflowProcessingJobRepository(verify_session).find_by_uuid(processing_job.uuid)

        expect(found).to(be_none)
    finally:
        async with session_maker() as cleanup_session:
            await SQLWorkflowProcessingJobRepository(cleanup_session).delete(processing_job.uuid, tenant_orm.uuid)
