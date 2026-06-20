from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from expects import be_a, be_below, be_empty, be_none, contain, equal, expect, have_length

from src.common.domain.enums.processing_job_events import (
    ProcessingJobEventType,
    DocumentStatus,
)
from src.common.domain.enums.workflows import (
    WorkflowProcessingJobStatus,
    WorkflowDocumentSource,
    WorkflowDocumentStatus,
)
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.application.processing_jobs.event_replayer import (
    ProcessingJobEventReplayer,
)
from src.workflows.domain.events import ProcessingJobEvent


def _set(
    *,
    workflow_id: UUID,
    tenant_id: UUID,
    status: WorkflowProcessingJobStatus,
    last_seq: int = 10,
    workflow_case_id: UUID | None = None,
    error: str | None = None,
    set_uuid: UUID | None = None,
) -> WorkflowProcessingJob:
    return WorkflowProcessingJob(
        uuid=set_uuid or uuid4(),
        temporal_workflow_id=f"WF#{uuid4().hex[:8]}",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        workflow_case_id=workflow_case_id,
        file_id=uuid4(),
        status=status,
        last_seq=last_seq,
        error=error,
        created_at=datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 5, 1, 12, 5, tzinfo=UTC),
    )


def _doc(
    *,
    set_id: UUID,
    workflow_id: UUID,
    tenant_id: UUID,
    processing_status: DocumentStatus,
    document_index: int = 0,
) -> WorkflowDocument:
    return WorkflowDocument(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        processing_job_id=set_id,
        file_name=f"doc-{document_index}.pdf",
        status=WorkflowDocumentStatus.EXTRACTED,
        source=WorkflowDocumentSource.BULK,
        processing_status=processing_status.value,
        document_index=document_index,
    )


@pytest.fixture
def workflow_id():
    return uuid4()


@pytest.fixture
def replayer(
    workflow_id,
    tenant_id,
    processing_job_repository,
    document_repository,
):
    return ProcessingJobEventReplayer(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        since_seq=0,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
    )


# --- 1. Empty result ----------------------------------------------------------


async def test_execute__no_sets_returns_empty(replayer, processing_job_repository):
    processing_job_repository.list_for_replay.return_value = []

    result = await replayer.execute()

    expect(result).to(be_empty)


# --- 2. COMPLETED set with 2 persisted docs -----------------------------------


async def test_execute__completed_set_emits_two_persisted_plus_one_completed(
    replayer,
    workflow_id,
    tenant_id,
    processing_job_repository,
    document_repository,
):
    set_uuid = uuid4()
    s = _set(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        status=WorkflowProcessingJobStatus.COMPLETED,
        last_seq=10,
        set_uuid=set_uuid,
    )
    docs = [
        _doc(
            set_id=set_uuid,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            processing_status=DocumentStatus.COMPLETED,
            document_index=i,
        )
        for i in range(2)
    ]
    processing_job_repository.list_for_replay.return_value = [s]
    document_repository.list_by_processing_job_ids.return_value = docs

    result = await replayer.execute()

    expect(result).to(have_length(3))
    types = [ev.type for ev in result]
    expect(types).to(contain(ProcessingJobEventType.DOCUMENT_PERSISTED))
    expect(types).to(contain(ProcessingJobEventType.COMPLETED))


async def test_execute__document_persisted_seqs_are_below_terminal_seq(
    replayer,
    workflow_id,
    tenant_id,
    processing_job_repository,
    document_repository,
):
    set_uuid = uuid4()
    s = _set(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        status=WorkflowProcessingJobStatus.COMPLETED,
        last_seq=10,
        set_uuid=set_uuid,
    )
    docs = [
        _doc(
            set_id=set_uuid,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            processing_status=DocumentStatus.COMPLETED,
            document_index=i,
        )
        for i in range(2)
    ]
    processing_job_repository.list_for_replay.return_value = [s]
    document_repository.list_by_processing_job_ids.return_value = docs

    result = await replayer.execute()

    persisted = [ev for ev in result if ev.type is ProcessingJobEventType.DOCUMENT_PERSISTED]
    for ev in persisted:
        expect(ev.seq).to(be_below(s.last_seq))


async def test_execute__terminal_event_keeps_set_last_seq(
    replayer,
    workflow_id,
    tenant_id,
    processing_job_repository,
    document_repository,
):
    s = _set(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        status=WorkflowProcessingJobStatus.COMPLETED,
        last_seq=42,
    )
    processing_job_repository.list_for_replay.return_value = [s]
    document_repository.list_by_processing_job_ids.return_value = []

    result = await replayer.execute()

    terminal = next(ev for ev in result if ev.type is ProcessingJobEventType.COMPLETED)
    expect(terminal.seq).to(equal(42))


# --- 3. FAILED set ------------------------------------------------------------


async def test_execute__failed_set_emits_one_failed_event(
    replayer,
    workflow_id,
    tenant_id,
    processing_job_repository,
    document_repository,
):
    s = _set(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        status=WorkflowProcessingJobStatus.FAILED,
        last_seq=5,
        error="lambda timeout",
    )
    processing_job_repository.list_for_replay.return_value = [s]
    document_repository.list_by_processing_job_ids.return_value = []

    result = await replayer.execute()

    expect(result).to(have_length(1))
    expect(result[0]).to(be_a(ProcessingJobEvent))
    expect(result[0].type).to(equal(ProcessingJobEventType.FAILED))


async def test_execute__failed_set_skips_non_terminal_doc_replay(
    replayer,
    workflow_id,
    tenant_id,
    processing_job_repository,
    document_repository,
):
    set_uuid = uuid4()
    s = _set(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        status=WorkflowProcessingJobStatus.FAILED,
        last_seq=5,
        set_uuid=set_uuid,
    )
    in_flight_doc = _doc(
        set_id=set_uuid,
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        processing_status=DocumentStatus.EXTRACTING,
    )
    processing_job_repository.list_for_replay.return_value = [s]
    document_repository.list_by_processing_job_ids.return_value = [in_flight_doc]

    result = await replayer.execute()

    types = [ev.type for ev in result]
    expect(types).not_to(contain(ProcessingJobEventType.DOCUMENT_PERSISTED))


# --- 4. RUNNING set (no terminal event) ---------------------------------------


@pytest.mark.parametrize(
    "active_status",
    [
        WorkflowProcessingJobStatus.PENDING,
        WorkflowProcessingJobStatus.RUNNING,
        WorkflowProcessingJobStatus.PROCESSING,
    ],
)
async def test_execute__non_terminal_set_emits_no_terminal_event(
    replayer,
    workflow_id,
    tenant_id,
    processing_job_repository,
    document_repository,
    active_status,
):
    s = _set(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        status=active_status,
        last_seq=3,
    )
    processing_job_repository.list_for_replay.return_value = [s]
    document_repository.list_by_processing_job_ids.return_value = []

    result = await replayer.execute()

    expect(result).to(be_empty)


# --- 5. Output sort: per-doc events come before terminal for the same set -----


async def test_execute__per_doc_events_precede_terminal_for_same_set(
    replayer,
    workflow_id,
    tenant_id,
    processing_job_repository,
    document_repository,
):
    set_uuid = uuid4()
    s = _set(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        status=WorkflowProcessingJobStatus.COMPLETED,
        last_seq=10,
        set_uuid=set_uuid,
    )
    docs = [
        _doc(
            set_id=set_uuid,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            processing_status=DocumentStatus.COMPLETED,
            document_index=i,
        )
        for i in range(3)
    ]
    processing_job_repository.list_for_replay.return_value = [s]
    document_repository.list_by_processing_job_ids.return_value = docs

    result = await replayer.execute()

    terminal_index = next(i for i, ev in enumerate(result) if ev.type is ProcessingJobEventType.COMPLETED)
    persisted_indices = [i for i, ev in enumerate(result) if ev.type is ProcessingJobEventType.DOCUMENT_PERSISTED]
    for idx in persisted_indices:
        expect(idx).to(be_below(terminal_index))


# --- 6. workflow_case_id propagation ------------------------------------------


async def test_execute__workflow_case_id_propagates_to_emitted_events(
    replayer,
    workflow_id,
    tenant_id,
    processing_job_repository,
    document_repository,
):
    case_id = uuid4()
    s = _set(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        status=WorkflowProcessingJobStatus.COMPLETED,
        last_seq=10,
        workflow_case_id=case_id,
    )
    processing_job_repository.list_for_replay.return_value = [s]
    document_repository.list_by_processing_job_ids.return_value = []

    result = await replayer.execute()

    expect(result).to(have_length(1))
    expect(result[0].workflow_case_id).to(equal(case_id))


async def test_execute__workflow_case_id_is_none_for_standard_workflow(
    replayer,
    workflow_id,
    tenant_id,
    processing_job_repository,
    document_repository,
):
    s = _set(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        status=WorkflowProcessingJobStatus.COMPLETED,
        last_seq=10,
        workflow_case_id=None,
    )
    processing_job_repository.list_for_replay.return_value = [s]
    document_repository.list_by_processing_job_ids.return_value = []

    result = await replayer.execute()

    expect(result[0].workflow_case_id).to(be_none)
