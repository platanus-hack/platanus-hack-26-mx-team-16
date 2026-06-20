from unittest.mock import AsyncMock, create_autospec
from uuid import uuid4

import pytest
from expects import contain, equal, expect

from src.common.application.helpers.webhooks.delivery import WebhookDeliveryResult
from src.common.domain.enums.webhooks import WebhookEventType, WorkflowEventDeliveryStatus
from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.webhook_destination import WebhookDestination
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.common.domain.models.workflow_event import WorkflowEvent
from src.workflows.application.processing_jobs.dispatch_webhooks import (
    DispatchProcessingJobWebhooks,
)
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.webhook_destination import WebhookDestinationRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)
from src.workflows.domain.repositories.workflow_event import WorkflowEventRepository

RUN_ID = "run-1"


def _workflow(tenant_uuid, **overrides) -> Workflow:
    defaults = {
        "uuid": uuid4(),
        "tenant_id": tenant_uuid,
        "name": "WF",
    }
    defaults.update(overrides)
    return Workflow(**defaults)


def _destination(tenant_uuid, workflow_uuid, **overrides) -> WebhookDestination:
    defaults = {
        "uuid": uuid4(),
        "tenant_id": tenant_uuid,
        "workflow_id": workflow_uuid,
        "name": "Default webhook",
        "url": "https://hooks.example.com/x",
        "enabled": True,
        "secret": "whsec_xxx",
        "subscribed_events": ["document.extracted", "document.failed"],
    }
    defaults.update(overrides)
    return WebhookDestination(**defaults)


def _processing_job(tenant_uuid, workflow_uuid) -> WorkflowProcessingJob:
    return WorkflowProcessingJob(
        uuid=uuid4(),
        temporal_workflow_id=RUN_ID,
        tenant_id=tenant_uuid,
        workflow_id=workflow_uuid,
        file_id=uuid4(),
    )


def _document(tenant_uuid, status=WorkflowDocumentStatus.EXTRACTED) -> WorkflowDocument:
    return WorkflowDocument(uuid=uuid4(), tenant_id=tenant_uuid, status=status)


def _fake_dispatcher():
    dispatcher = AsyncMock()
    dispatcher.deliver = AsyncMock(
        return_value=WebhookDeliveryResult(delivered=True, attempts=1, status_code=200)
    )
    return dispatcher


def _make_use_case(*, workflow, processing_job, documents, destinations=None, existing_event=None):
    workflow_repository = create_autospec(spec=WorkflowRepository, spec_set=True, instance=True)
    workflow_repository.find_by_id = AsyncMock(return_value=workflow)

    set_repo = create_autospec(spec=WorkflowProcessingJobRepository, spec_set=True, instance=True)
    set_repo.find_by_uuid = AsyncMock(return_value=processing_job)

    doc_repo = create_autospec(spec=WorkflowDocumentRepository, spec_set=True, instance=True)
    doc_repo.list_by_processing_job = AsyncMock(return_value=documents)

    type_repo = create_autospec(spec=DocumentTypeRepository, spec_set=True, instance=True)
    type_repo.find_by_ids = AsyncMock(return_value={})

    event_repo = create_autospec(spec=WorkflowEventRepository, spec_set=True, instance=True)
    event_repo.find_by_unique_destination = AsyncMock(return_value=existing_event)
    event_repo.create = AsyncMock(side_effect=lambda event: event)
    event_repo.update = AsyncMock(side_effect=lambda event: event)

    dest_repo = create_autospec(spec=WebhookDestinationRepository, spec_set=True, instance=True)
    dest_repo.list_enabled_for_event = AsyncMock(return_value=destinations or [])

    dispatcher = _fake_dispatcher()
    use_case = DispatchProcessingJobWebhooks(
        processing_job_id=processing_job.uuid,
        workflow_id=workflow.uuid,
        run_id=RUN_ID,
        final_status="COMPLETED",
        workflow_repository=workflow_repository,
        processing_job_repository=set_repo,
        document_repository=doc_repo,
        document_type_repository=type_repo,
        workflow_event_repository=event_repo,
        webhook_destination_repository=dest_repo,
        dispatcher=dispatcher,
    )
    return use_case, event_repo, dispatcher


@pytest.fixture
def tenant_uuid():
    return uuid4()


async def test_execute__no_enabled_destinations_creates_no_events(tenant_uuid):
    workflow = _workflow(tenant_uuid)
    processing_job = _processing_job(tenant_uuid, workflow.uuid)
    use_case, event_repo, dispatcher = _make_use_case(
        workflow=workflow,
        processing_job=processing_job,
        documents=[_document(tenant_uuid)],
        destinations=[],
    )

    await use_case.execute()

    expect(event_repo.create.await_count).to(equal(0))
    expect(dispatcher.deliver.await_count).to(equal(0))


async def test_execute__fans_out_to_each_enabled_destination(tenant_uuid):
    workflow = _workflow(tenant_uuid)
    processing_job = _processing_job(tenant_uuid, workflow.uuid)
    document = _document(tenant_uuid, WorkflowDocumentStatus.EXTRACTED)
    dest_a = _destination(tenant_uuid, workflow.uuid, url="https://a.example.com")
    dest_b = _destination(tenant_uuid, workflow.uuid, url="https://b.example.com")
    use_case, event_repo, dispatcher = _make_use_case(
        workflow=workflow,
        processing_job=processing_job,
        documents=[document],
        destinations=[dest_a, dest_b],
    )

    await use_case.execute()

    expect(event_repo.create.await_count).to(equal(2))
    expect(dispatcher.deliver.await_count).to(equal(2))
    delivered_urls = [call.kwargs["url"] for call in dispatcher.deliver.await_args_list]
    expect(delivered_urls).to(contain("https://a.example.com"))
    expect(delivered_urls).to(contain("https://b.example.com"))


async def test_execute__subscribed_delivers_and_marks_delivered(tenant_uuid):
    workflow = _workflow(tenant_uuid)
    processing_job = _processing_job(tenant_uuid, workflow.uuid)
    document = _document(tenant_uuid, WorkflowDocumentStatus.EXTRACTED)
    destination = _destination(tenant_uuid, workflow.uuid)
    use_case, event_repo, dispatcher = _make_use_case(
        workflow=workflow,
        processing_job=processing_job,
        documents=[document],
        destinations=[destination],
    )

    await use_case.execute()

    final_event = event_repo.update.await_args.args[0]
    expect(dispatcher.deliver.await_count).to(equal(1))
    expect(dispatcher.deliver.await_args.kwargs["url"]).to(equal(destination.url))
    expect(dispatcher.deliver.await_args.kwargs["secret"]).to(equal(destination.secret))
    expect(final_event.delivery_status).to(equal(WorkflowEventDeliveryStatus.DELIVERED))
    expect(final_event.destination_id).to(equal(destination.uuid))


async def test_execute__skips_already_delivered_event_for_run(tenant_uuid):
    workflow = _workflow(tenant_uuid)
    processing_job = _processing_job(tenant_uuid, workflow.uuid)
    document = _document(tenant_uuid, WorkflowDocumentStatus.EXTRACTED)
    destination = _destination(tenant_uuid, workflow.uuid)
    existing = WorkflowEvent(
        uuid=uuid4(),
        tenant_id=tenant_uuid,
        event_id="evt_existing",
        event_type=WebhookEventType.DOCUMENT_EXTRACTED,
        workflow_id=workflow.uuid,
        document_id=document.uuid,
        destination_id=destination.uuid,
        idempotency_key=RUN_ID,
        document_status="EXTRACTED",
        payload={},
        delivery_status=WorkflowEventDeliveryStatus.DELIVERED,
    )
    use_case, event_repo, dispatcher = _make_use_case(
        workflow=workflow,
        processing_job=processing_job,
        documents=[document],
        destinations=[destination],
        existing_event=existing,
    )

    await use_case.execute()

    expect(event_repo.create.await_count).to(equal(0))
    expect(dispatcher.deliver.await_count).to(equal(0))
