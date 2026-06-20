from unittest.mock import AsyncMock, MagicMock, create_autospec
from uuid import uuid4

import pytest
from expects import be_empty, equal, expect, have_length

from src.common.domain.enums.workflows import (
    WorkflowProcessingJobStatus,
    WorkflowDocumentSource,
    WorkflowDocumentStatus,
)
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.application.document_processing.runner import (
    RunAndPersistDocumentProcessing,
)
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)


@pytest.fixture
def processing_job():
    return WorkflowProcessingJob(
        uuid=uuid4(),
        temporal_workflow_id="CASE#aaa_FILE#bbb",
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        workflow_case_id=uuid4(),
        file_id=uuid4(),
        status=WorkflowProcessingJobStatus.PENDING,
    )


@pytest.fixture
def processing_job_repository(processing_job):
    repo = create_autospec(spec=WorkflowProcessingJobRepository, spec_set=True, instance=True)
    repo.claim.return_value = processing_job
    repo.mark_done.return_value = None
    repo.mark_failed.return_value = None
    return repo


def _persisted_doc(processing_job: WorkflowProcessingJob) -> WorkflowDocument:
    """A WorkflowDocument shaped like one the worker activities would have
    persisted/finalized for this document set."""
    return WorkflowDocument(
        uuid=uuid4(),
        tenant_id=processing_job.tenant_id,
        workflow_id=processing_job.workflow_id,
        case_id=processing_job.workflow_case_id,
        file_id=processing_job.file_id,
        document_type_id=uuid4(),
        file_name="document",
        status=WorkflowDocumentStatus.EXTRACTED,
        source=WorkflowDocumentSource.BULK,
        extraction={"nombres": "LAURA"},
    )


@pytest.fixture
def document_repository(processing_job):
    repo = create_autospec(spec=WorkflowDocumentRepository, spec_set=True, instance=True)
    repo.list_by_processing_job.return_value = [_persisted_doc(processing_job), _persisted_doc(processing_job)]
    return repo


@pytest.fixture
def temporal_client_with_output():
    """Returns a callable that builds a TemporalClient mock whose
    handle.result() resolves to the provided output dict."""

    def _build(output: dict) -> MagicMock:
        client = MagicMock()
        handle = MagicMock()
        handle.result = AsyncMock(return_value=output)
        client.get_workflow_handle = MagicMock(return_value=handle)
        return client

    return _build


def _success_output(processing_job: WorkflowProcessingJob) -> dict:
    return {
        "job_id": processing_job.temporal_workflow_id,
        "extract_text_source": "s3://bucket/extract_text.json",
        "classify_pages_source": "s3://bucket/classify_pages.json",
        "extract_fields": {
            "status": "success",
            "extractions": [],
            "errors": [],
            "metadata": {},
        },
        "validate_extraction": {
            "status": "success",
            "validations": [],
            "errors": [],
            "metadata": {},
        },
    }


async def test_execute__returns_documents_persisted_by_worker(
    processing_job, processing_job_repository, document_repository, temporal_client_with_output
):
    use_case = RunAndPersistDocumentProcessing(
        processing_job=processing_job,
        extraction_timeout_seconds=60,
        temporal_client=temporal_client_with_output(_success_output(processing_job)),
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
    )

    documents = await use_case.execute()

    expect(documents).to(have_length(2))
    document_repository.list_by_processing_job.assert_awaited_once_with(processing_job.uuid)


async def test_execute__never_creates_workflow_documents(
    processing_job, processing_job_repository, document_repository, temporal_client_with_output
):
    """Regression: the worker activities are the single writer of
    workflow_documents; the runner must not call .create() (which would
    duplicate the rows the worker already inserted)."""
    use_case = RunAndPersistDocumentProcessing(
        processing_job=processing_job,
        extraction_timeout_seconds=60,
        temporal_client=temporal_client_with_output(_success_output(processing_job)),
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
    )

    await use_case.execute()

    expect(document_repository.create.await_count).to(equal(0))


async def test_execute__marks_done_with_summary(
    processing_job, processing_job_repository, document_repository, temporal_client_with_output
):
    use_case = RunAndPersistDocumentProcessing(
        processing_job=processing_job,
        extraction_timeout_seconds=60,
        temporal_client=temporal_client_with_output(_success_output(processing_job)),
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
    )

    await use_case.execute()

    processing_job_repository.mark_done.assert_awaited_once()
    args = processing_job_repository.mark_done.await_args.args
    expect(args[0]).to(equal(processing_job.uuid))
    summary = args[1]
    expect(summary["documents_created"]).to(equal(2))
    expect(summary["extract_fields_status"]).to(equal("success"))


async def test_execute__extract_fields_error_marks_failed_and_skips_read(
    processing_job, processing_job_repository, document_repository, temporal_client_with_output
):
    output = _success_output(processing_job)
    output["extract_fields"] = {
        "status": "error",
        "error_code": "extract_fields.no_documents",
        "message": "No documents to process",
        "extractions": [],
        "errors": [],
        "metadata": {},
    }

    use_case = RunAndPersistDocumentProcessing(
        processing_job=processing_job,
        extraction_timeout_seconds=60,
        temporal_client=temporal_client_with_output(output),
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
    )

    with pytest.raises(RuntimeError):
        await use_case.execute()

    processing_job_repository.mark_failed.assert_awaited_once()
    expect(document_repository.list_by_processing_job.await_count).to(equal(0))
    expect(processing_job_repository.mark_done.await_count).to(equal(0))


async def test_execute__already_claimed_returns_empty_and_skips_workflow_call(processing_job, document_repository):
    processing_job_repo = create_autospec(spec=WorkflowProcessingJobRepository, spec_set=True, instance=True)
    processing_job_repo.claim.return_value = None  # otro worker ya lo agarró

    temporal_client = MagicMock()
    handle = MagicMock()
    handle.result = AsyncMock()
    temporal_client.get_workflow_handle = MagicMock(return_value=handle)

    use_case = RunAndPersistDocumentProcessing(
        processing_job=processing_job,
        extraction_timeout_seconds=60,
        temporal_client=temporal_client,
        processing_job_repository=processing_job_repo,
        document_repository=document_repository,
    )

    result = await use_case.execute()

    expect(result).to(be_empty)
    expect(handle.result.await_count).to(equal(0))
    expect(document_repository.list_by_processing_job.await_count).to(equal(0))
    expect(processing_job_repo.mark_done.await_count).to(equal(0))
    expect(processing_job_repo.mark_failed.await_count).to(equal(0))
