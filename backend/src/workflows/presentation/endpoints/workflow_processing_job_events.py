from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from src.common.database.models.processing.file_upload import DocumentORM
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import (
    AsyncSessionDep,
    RedisClientDep,
    get_app_context,
)
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.sse.streaming import stream_sse
from src.workflows.application.processing_jobs.event_replayer import (
    ProcessingJobEventReplayer,
)
from src.workflows.domain.events import processing_job_channel
from src.workflows.presentation.presenters.processing_job_event import (
    ProcessingJobEventPresenter,
)


async def stream_processing_job_events(
    request: Request,
    workflow_id: UUID,
    redis_client: RedisClientDep,
    session: AsyncSessionDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    since_seq: int = Query(default=0, ge=0),
    workflow_case_id: UUID | None = Query(default=None, alias="workflowCaseId"),
) -> EventSourceResponse:
    workflow = await app_context.domain.workflow_repository.find_by_id(workflow_id, tenant.uuid)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Resolve filenames so replayed terminal events can carry them — the
    # `dispatched` event (which normally seeds the UI's title) is not part
    # of the replay window for historical sets.
    sets_for_replay = await app_context.domain.processing_job_repository.list_for_replay(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        since_seq=since_seq,
        workflow_case_id=workflow_case_id,
    )
    file_names_by_set_id: dict[UUID, str | None] = {}
    if sets_for_replay:
        file_ids = list({s.file_id for s in sets_for_replay if s.file_id})
        if file_ids:
            rows = (await session.execute(select(DocumentORM).where(DocumentORM.uuid.in_(file_ids)))).scalars().all()
            files_by_id = {row.uuid: row.file_name for row in rows}
            file_names_by_set_id = {s.uuid: files_by_id.get(s.file_id) for s in sets_for_replay}

    replay_events = await ProcessingJobEventReplayer(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        since_seq=since_seq,
        workflow_case_id=workflow_case_id,
        processing_job_repository=app_context.domain.processing_job_repository,
        document_repository=app_context.domain.document_repository,
        file_names_by_set_id=file_names_by_set_id,
    ).execute()

    # Per-set seq dedupe: processing-jobs reuse seq within (set_id, seq)
    # namespace, so the global dedupe in `stream_sse` is not enough.
    replayed_seqs_by_set: dict[str, set[int]] = {}
    for ev in replay_events:
        replayed_seqs_by_set.setdefault(str(ev.processing_job_id), set()).add(ev.seq)

    presented_replay = [ProcessingJobEventPresenter(instance=ev).to_dict for ev in replay_events]

    async def replay() -> AsyncIterator[dict[str, Any]]:
        for event_dict in presented_replay:
            yield event_dict

    return stream_sse(
        channel=processing_job_channel(workflow_id),
        redis_client=redis_client,
        request=request,
        replay=replay,
        filter_fn=_make_filter_fn(replayed_seqs_by_set, workflow_case_id),
    )


def _make_filter_fn(
    replayed_seqs_by_set: dict[str, set[int]],
    workflow_case_id: UUID | None,
):
    case_id_str = str(workflow_case_id) if workflow_case_id is not None else None

    def passes(event: dict[str, Any]) -> bool:
        if case_id_str is not None and event.get("workflow_case_id") != case_id_str:
            return False
        seq = event.get("seq")
        processing_job_id = event.get("processing_job_id")
        if (
            isinstance(seq, int)
            and isinstance(processing_job_id, str)
            and seq in replayed_seqs_by_set.get(processing_job_id, set())
        ):
            return False
        return True

    return passes
