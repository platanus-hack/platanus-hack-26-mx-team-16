"""Tests for ``CaseFieldReExtractionStarter``.

Critical guards (one behavior per test):

* `NoDocumentsToAnalyzeError` when the case has no document sets.
* `ExtractionInProgressError` when any set is in flight (PENDING/PROCESSING/RUNNING).
* `AnalysisAlreadyRunningError` when an analysis run is active for the case.
* `ClassifiedPagesMissingError` when a set has no `classified_pages` key.
* `WorkflowPipelineNotConfiguredError` (409) when the workflow's OWN pipeline
  is missing or has no active version (ADR 0002, resolved via
  ``find_by_workflow(workflow_id, tenant_id)``).
* Happy path: dispatches one ``PipelineInterpreterWorkflow`` per set with the
  workflow's sealed pipeline + ``entry_point="reextract"`` +
  ``initial_artifacts``/``starting_seq`` (run extract-only).
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, create_autospec
from uuid import uuid4

import pytest
from expects import be, be_a, equal, expect, have_length
from temporalio.client import Client as TemporalClient

from src.common.domain.entities.workflows.pipeline_run import PipelineRunInput
from src.common.domain.enums.pipelines import PipelineKind
from src.common.domain.enums.workflow_rules import WorkflowAnalysisRunStatus as AnalysisRunStatus
from src.common.domain.enums.workflows import (
    WorkflowProcessingJobStatus,
    WorkflowDocumentSource,
    WorkflowDocumentStatus,
)
from src.common.domain.exceptions.processing import (
    AnalysisAlreadyRunningError,
    ExtractionInProgressError,
    NoDocumentsToAnalyzeError,
    WorkflowPipelineNotConfiguredError,
)
from src.common.domain.models.processing.workflow_analysis_run import (
    WorkflowAnalysisRun as AnalysisRun,
)
from src.common.domain.models.processing.document_type import DocumentType
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.application.processing_jobs.re_extractor import (
    CaseFieldReExtractionStarter,
    ClassifiedPagesMissingError,
)
from src.workflows.domain.models.pipeline import Pipeline
from src.workflows.domain.recipes import REEXTRACT_PIPELINE_SLUG
from src.workflows.presentation.workflows.pipeline_interpreter import (
    PipelineInterpreterWorkflow,
)

# ─── Builders ────────────────────────────────────────────────────────────────


def _workflow(tenant_id) -> Workflow:
    return Workflow(uuid=uuid4(), tenant_id=tenant_id, name="Test Workflow")


def _case(tenant_id, workflow_id) -> WorkflowCase:
    return WorkflowCase(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="Case 1",
    )


def _doc_type(tenant_id, workflow_id) -> DocumentType:
    return DocumentType(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="Evaluacion",
        slug="evaluacion",
    )


def _recipe(tenant_id, workflow_id, *, current_version=1) -> Pipeline:
    return Pipeline(
        uuid=uuid4(),
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        slug=REEXTRACT_PIPELINE_SLUG,
        name="Re-extracción de campos",
        kind=PipelineKind.EXTRACTION,
        current_version=current_version,
    )


def _processing_job(
    tenant_id,
    workflow_id,
    case_id,
    *,
    status=WorkflowProcessingJobStatus.COMPLETED,
    classified_pages: str | None = "s3://bucket/classified.json",
    last_seq: int = 16,
) -> WorkflowProcessingJob:
    return WorkflowProcessingJob(
        uuid=uuid4(),
        temporal_workflow_id=f"job-{uuid4().hex[:8]}",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        workflow_case_id=case_id,
        file_id=uuid4(),
        status=status,
        classified_pages=classified_pages,
        last_seq=last_seq,
    )


def _document(
    tenant_id,
    workflow_id,
    case_id,
    processing_job_id,
    document_type_id,
    *,
    document_index: int = 0,
) -> WorkflowDocument:
    return WorkflowDocument(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        case_id=case_id,
        document_type_id=document_type_id,
        status=WorkflowDocumentStatus.EXTRACTED,
        source=WorkflowDocumentSource.BULK,
        processing_job_id=processing_job_id,
        document_index=document_index,
        page_range={"from": document_index + 1, "to": document_index + 1},
    )


def _active_run(tenant_id, case_id, workflow_id) -> AnalysisRun:
    return AnalysisRun(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        workflow_case_id=case_id,
        status=AnalysisRunStatus.RUNNING,
        created_at=datetime.now(UTC),
    )


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def temporal_client_mock():
    """Async mock that returns a stub workflow handle on `start_workflow`.

    The use case only reads `handle.id`, so a MagicMock with a fixed id
    is enough — no need to spec against `WorkflowHandle` (which has a
    private constructor and breaks autospec).
    """
    client = create_autospec(spec=TemporalClient, spec_set=False, instance=True)
    handle = MagicMock()
    handle.id = "REEXTRACT#stub"
    client.start_workflow = AsyncMock(return_value=handle)
    return client


@pytest.fixture
def workflow(tenant_id):
    return _workflow(tenant_id)


@pytest.fixture
def case(tenant_id, workflow):
    return _case(tenant_id, workflow.uuid)


@pytest.fixture
def doc_type(tenant_id, workflow):
    return _doc_type(tenant_id, workflow.uuid)


@pytest.fixture
def re_extract_recipe(tenant_id, workflow):
    return _recipe(tenant_id, workflow.uuid, current_version=2)


def _build(
    *,
    tenant_id,
    workflow,
    case,
    sets,
    documents,
    doc_types,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_repository,
    document_type_repository,
    analysis_run_repository,
    pipeline_repository,
    temporal_client_mock,
    active_run=None,
    recipe=None,
) -> CaseFieldReExtractionStarter:
    workflow_repository.find_by_id.return_value = workflow
    workflow_case_repository.find_by_id.return_value = case
    processing_job_repository.list_by_workflow.return_value = sets
    document_repository.list_by_processing_job_ids.return_value = documents
    document_type_repository.list_by_workflow.return_value = doc_types
    analysis_run_repository.find_active_for_case.return_value = active_run
    pipeline_repository.find_by_workflow.return_value = recipe
    return CaseFieldReExtractionStarter(
        tenant_id=tenant_id,
        workflow_id=workflow.uuid,
        case_id=case.uuid,
        temporal_client=temporal_client_mock,
        task_queue="document-processing",
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        analysis_run_repository=analysis_run_repository,
        pipeline_repository=pipeline_repository,
    )


# ─── Guards ──────────────────────────────────────────────────────────────────


async def test_execute__no_sets_raises(
    tenant_id,
    workflow,
    case,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_repository,
    document_type_repository,
    analysis_run_repository,
    pipeline_repository,
    temporal_client_mock,
    re_extract_recipe,
):
    use_case = _build(
        tenant_id=tenant_id,
        workflow=workflow,
        case=case,
        sets=[],
        documents=[],
        doc_types=[],
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        analysis_run_repository=analysis_run_repository,
        pipeline_repository=pipeline_repository,
        temporal_client_mock=temporal_client_mock,
        recipe=re_extract_recipe,
    )

    with pytest.raises(NoDocumentsToAnalyzeError):
        await use_case.execute()


@pytest.mark.parametrize(
    "in_flight_status",
    [
        WorkflowProcessingJobStatus.PENDING,
        WorkflowProcessingJobStatus.RUNNING,
        WorkflowProcessingJobStatus.PROCESSING,
    ],
)
async def test_execute__set_in_flight_raises(
    in_flight_status,
    tenant_id,
    workflow,
    case,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_repository,
    document_type_repository,
    analysis_run_repository,
    pipeline_repository,
    temporal_client_mock,
    re_extract_recipe,
):
    in_flight = _processing_job(tenant_id, workflow.uuid, case.uuid, status=in_flight_status)

    use_case = _build(
        tenant_id=tenant_id,
        workflow=workflow,
        case=case,
        sets=[in_flight],
        documents=[],
        doc_types=[],
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        analysis_run_repository=analysis_run_repository,
        pipeline_repository=pipeline_repository,
        temporal_client_mock=temporal_client_mock,
        recipe=re_extract_recipe,
    )

    with pytest.raises(ExtractionInProgressError):
        await use_case.execute()


async def test_execute__active_analysis_run_raises(
    tenant_id,
    workflow,
    case,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_repository,
    document_type_repository,
    analysis_run_repository,
    pipeline_repository,
    temporal_client_mock,
    re_extract_recipe,
):
    set_a = _processing_job(tenant_id, workflow.uuid, case.uuid)

    use_case = _build(
        tenant_id=tenant_id,
        workflow=workflow,
        case=case,
        sets=[set_a],
        documents=[],
        doc_types=[],
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        analysis_run_repository=analysis_run_repository,
        pipeline_repository=pipeline_repository,
        temporal_client_mock=temporal_client_mock,
        active_run=_active_run(tenant_id, case.uuid, workflow.uuid),
        recipe=re_extract_recipe,
    )

    with pytest.raises(AnalysisAlreadyRunningError):
        await use_case.execute()


async def test_execute__missing_re_extract_recipe_raises_409(
    tenant_id,
    workflow,
    case,
    doc_type,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_repository,
    document_type_repository,
    analysis_run_repository,
    pipeline_repository,
    temporal_client_mock,
):
    # Arrange — el tenant no tiene la receta `field-re-extraction` sembrada (E1)
    set_a = _processing_job(tenant_id, workflow.uuid, case.uuid)
    doc = _document(tenant_id, workflow.uuid, case.uuid, set_a.uuid, doc_type.uuid)
    use_case = _build(
        tenant_id=tenant_id,
        workflow=workflow,
        case=case,
        sets=[set_a],
        documents=[doc],
        doc_types=[doc_type],
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        analysis_run_repository=analysis_run_repository,
        pipeline_repository=pipeline_repository,
        temporal_client_mock=temporal_client_mock,
        recipe=None,
    )

    # Act / Assert
    with pytest.raises(WorkflowPipelineNotConfiguredError):
        await use_case.execute()

    pipeline_repository.find_by_workflow.assert_awaited_once_with(workflow.uuid, tenant_id)
    expect(temporal_client_mock.start_workflow.await_count).to(equal(0))


async def test_execute__recipe_without_current_version_raises_409(
    tenant_id,
    workflow,
    case,
    doc_type,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_repository,
    document_type_repository,
    analysis_run_repository,
    pipeline_repository,
    temporal_client_mock,
):
    set_a = _processing_job(tenant_id, workflow.uuid, case.uuid)
    doc = _document(tenant_id, workflow.uuid, case.uuid, set_a.uuid, doc_type.uuid)
    use_case = _build(
        tenant_id=tenant_id,
        workflow=workflow,
        case=case,
        sets=[set_a],
        documents=[doc],
        doc_types=[doc_type],
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        analysis_run_repository=analysis_run_repository,
        pipeline_repository=pipeline_repository,
        temporal_client_mock=temporal_client_mock,
        recipe=_recipe(tenant_id, workflow.uuid, current_version=None),
    )

    with pytest.raises(WorkflowPipelineNotConfiguredError):
        await use_case.execute()


async def test_execute__set_without_classified_pages_raises(
    tenant_id,
    workflow,
    case,
    doc_type,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_repository,
    document_type_repository,
    analysis_run_repository,
    pipeline_repository,
    temporal_client_mock,
    re_extract_recipe,
):
    set_without_classify = _processing_job(tenant_id, workflow.uuid, case.uuid, classified_pages=None)
    doc = _document(tenant_id, workflow.uuid, case.uuid, set_without_classify.uuid, doc_type.uuid)

    use_case = _build(
        tenant_id=tenant_id,
        workflow=workflow,
        case=case,
        sets=[set_without_classify],
        documents=[doc],
        doc_types=[doc_type],
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        analysis_run_repository=analysis_run_repository,
        pipeline_repository=pipeline_repository,
        temporal_client_mock=temporal_client_mock,
        recipe=re_extract_recipe,
    )

    with pytest.raises(ClassifiedPagesMissingError):
        await use_case.execute()


# ─── Happy path ──────────────────────────────────────────────────────────────


async def test_execute__dispatches_one_temporal_workflow_per_set(
    tenant_id,
    workflow,
    case,
    doc_type,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_repository,
    document_type_repository,
    analysis_run_repository,
    pipeline_repository,
    temporal_client_mock,
    re_extract_recipe,
):
    set_a = _processing_job(tenant_id, workflow.uuid, case.uuid)
    set_b = _processing_job(tenant_id, workflow.uuid, case.uuid)
    docs = [
        _document(tenant_id, workflow.uuid, case.uuid, set_a.uuid, doc_type.uuid, document_index=0),
        _document(tenant_id, workflow.uuid, case.uuid, set_b.uuid, doc_type.uuid, document_index=0),
    ]

    use_case = _build(
        tenant_id=tenant_id,
        workflow=workflow,
        case=case,
        sets=[set_a, set_b],
        documents=docs,
        doc_types=[doc_type],
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        analysis_run_repository=analysis_run_repository,
        pipeline_repository=pipeline_repository,
        temporal_client_mock=temporal_client_mock,
        recipe=re_extract_recipe,
    )

    result = await use_case.execute()

    expect(temporal_client_mock.start_workflow.call_count).to(equal(2))
    expect(result["dispatched"]).to(have_length(2))
    dispatched_set_ids = {entry["setId"] for entry in result["dispatched"]}
    expect(dispatched_set_ids).to(equal({str(set_a.uuid), str(set_b.uuid)}))


async def test_execute__skips_set_with_no_persisted_documents(
    tenant_id,
    workflow,
    case,
    doc_type,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_repository,
    document_type_repository,
    analysis_run_repository,
    pipeline_repository,
    temporal_client_mock,
    re_extract_recipe,
):
    set_with_docs = _processing_job(tenant_id, workflow.uuid, case.uuid)
    set_empty = _processing_job(tenant_id, workflow.uuid, case.uuid)
    docs = [
        _document(tenant_id, workflow.uuid, case.uuid, set_with_docs.uuid, doc_type.uuid),
    ]

    use_case = _build(
        tenant_id=tenant_id,
        workflow=workflow,
        case=case,
        sets=[set_with_docs, set_empty],
        documents=docs,
        doc_types=[doc_type],
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        analysis_run_repository=analysis_run_repository,
        pipeline_repository=pipeline_repository,
        temporal_client_mock=temporal_client_mock,
        recipe=re_extract_recipe,
    )

    result = await use_case.execute()

    expect(temporal_client_mock.start_workflow.call_count).to(equal(1))
    expect(result["dispatched"]).to(have_length(1))
    expect(result["dispatched"][0]["setId"]).to(equal(str(set_with_docs.uuid)))


async def test_execute__seeds_interpreter_run_with_initial_artifacts(
    tenant_id,
    workflow,
    case,
    doc_type,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_repository,
    document_type_repository,
    analysis_run_repository,
    pipeline_repository,
    temporal_client_mock,
    re_extract_recipe,
):
    """El run extract-only despacha el intérprete con la receta
    ``field-re-extraction`` sellada y los artefactos del run original
    (``classify_pages`` + ``persisted_docs``) pre-sembrados, continuando el
    ``seq`` del set para que el replay del FE no descarte eventos."""
    expected_key = "s3://bucket/classified-pages-abc.json"
    set_a = _processing_job(
        tenant_id,
        workflow.uuid,
        case.uuid,
        classified_pages=expected_key,
        last_seq=42,
    )
    docs = [
        _document(tenant_id, workflow.uuid, case.uuid, set_a.uuid, doc_type.uuid, document_index=1),
        _document(tenant_id, workflow.uuid, case.uuid, set_a.uuid, doc_type.uuid, document_index=0),
    ]

    use_case = _build(
        tenant_id=tenant_id,
        workflow=workflow,
        case=case,
        sets=[set_a],
        documents=docs,
        doc_types=[doc_type],
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        analysis_run_repository=analysis_run_repository,
        pipeline_repository=pipeline_repository,
        temporal_client_mock=temporal_client_mock,
        recipe=re_extract_recipe,
    )

    await use_case.execute()

    call_args = temporal_client_mock.start_workflow.call_args
    expect(call_args.args[0]).to(be(PipelineInterpreterWorkflow.run))
    workflow_input = call_args.args[1]
    expect(workflow_input).to(be_a(PipelineRunInput))
    # Receta sellada al despachar: pipeline PROPIO del workflow + versión activa,
    # con el entry point que selecciona el sub-segmento extract-only.
    expect(workflow_input.pipeline_id).to(equal(re_extract_recipe.uuid))
    expect(workflow_input.version).to(equal(re_extract_recipe.current_version))
    expect(workflow_input.entry_point).to(equal("reextract"))
    # Artefactos del run original pre-sembrados — sin re-OCR ni re-clasificación
    expect(workflow_input.initial_artifacts["classify_pages"]).to(equal({"output_uri": expected_key}))
    persisted = workflow_input.initial_artifacts["persisted_docs"]
    expect(persisted).to(have_length(2))
    # Ordered by document_index so the lambda response reconciles deterministically.
    expect([d["document_index"] for d in persisted]).to(equal([0, 1]))
    expect({d["document_id"] for d in persisted}).to(equal({str(doc.uuid) for doc in docs}))
    # El seq continúa el del set original
    expect(workflow_input.starting_seq).to(equal(42))
    expect(workflow_input.document.processing_job_uuid).to(equal(set_a.uuid))
    expect(workflow_input.document.persist).to(equal(True))


async def test_execute__job_id_uses_reextract_namespace(
    tenant_id,
    workflow,
    case,
    doc_type,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_repository,
    document_type_repository,
    analysis_run_repository,
    pipeline_repository,
    temporal_client_mock,
    re_extract_recipe,
):
    set_a = _processing_job(tenant_id, workflow.uuid, case.uuid)
    docs = [
        _document(tenant_id, workflow.uuid, case.uuid, set_a.uuid, doc_type.uuid),
    ]

    use_case = _build(
        tenant_id=tenant_id,
        workflow=workflow,
        case=case,
        sets=[set_a],
        documents=docs,
        doc_types=[doc_type],
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        processing_job_repository=processing_job_repository,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        analysis_run_repository=analysis_run_repository,
        pipeline_repository=pipeline_repository,
        temporal_client_mock=temporal_client_mock,
        recipe=re_extract_recipe,
    )

    await use_case.execute()

    job_id_kwarg = temporal_client_mock.start_workflow.call_args.kwargs["id"]
    # The REEXTRACT# prefix prevents collisions with the original
    # CASE#…_FILE#… processing job id, so retries don't trample running
    # extraction workflows.
    expect(job_id_kwarg.startswith("REEXTRACT#")).to(equal(True))
