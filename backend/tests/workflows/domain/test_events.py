from datetime import datetime, timezone
from uuid import uuid4

from expects import be_none, equal, expect

from src.common.domain.enums.processing_job_events import ProcessingJobEventType
from src.workflows.domain.events import ProcessingJobEvent, processing_job_channel


def test_channel__matches_helper_for_workflow():
    workflow_id = uuid4()
    processing_job_id = uuid4()
    event = ProcessingJobEvent.build(
        type=ProcessingJobEventType.DISPATCHED,
        seq=1,
        ts=datetime(2026, 4, 28, tzinfo=timezone.utc),
        workflow_id=workflow_id,
        processing_job_id=processing_job_id,
        payload={},
    )

    expect(event.channel).to(equal(f"workflow:{workflow_id}:processing_jobs:events"))
    expect(event.channel).to(equal(processing_job_channel(workflow_id)))


def test_build__workflow_case_id_and_document_id_are_optional():
    event = ProcessingJobEvent.build(
        type=ProcessingJobEventType.DISPATCHED,
        seq=1,
        ts=datetime(2026, 4, 28, tzinfo=timezone.utc),
        workflow_id=uuid4(),
        processing_job_id=uuid4(),
        payload={},
    )

    expect(event.workflow_case_id).to(be_none)
    expect(event.document_id).to(be_none)


def test_build__carries_workflow_case_id_and_document_id_when_provided():
    workflow_case_id = uuid4()
    document_id = uuid4()
    event = ProcessingJobEvent.build(
        type=ProcessingJobEventType.DOCUMENT_PERSISTED,
        seq=12,
        ts=datetime(2026, 4, 28, tzinfo=timezone.utc),
        workflow_id=uuid4(),
        processing_job_id=uuid4(),
        workflow_case_id=workflow_case_id,
        document_id=document_id,
        payload={"summary": {}},
    )

    expect(event.workflow_case_id).to(equal(workflow_case_id))
    expect(event.document_id).to(equal(document_id))


def test_seq_is_preserved_in_serialization():
    event = ProcessingJobEvent.build(
        type=ProcessingJobEventType.STEP_STARTED,
        seq=42,
        ts=datetime(2026, 4, 28, tzinfo=timezone.utc),
        workflow_id=uuid4(),
        processing_job_id=uuid4(),
        payload={"step": "extract_text", "pct": 0},
    )

    serialized = event.model_dump()

    expect(serialized["seq"]).to(equal(42))
    expect(serialized["type"]).to(equal(ProcessingJobEventType.STEP_STARTED.value))
