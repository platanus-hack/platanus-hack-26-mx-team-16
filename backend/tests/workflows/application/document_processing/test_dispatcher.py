from unittest.mock import AsyncMock, MagicMock, create_autospec
from uuid import uuid4

import pytest
from expects import be, be_a, contain, equal, expect
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client as TemporalClient
from temporalio.exceptions import WorkflowAlreadyStartedError

from src.common.domain.entities.workflows.pipeline_run import PipelineRunInput
from src.common.domain.enums.pipelines import PipelineKind
from src.common.domain.enums.workflows import WorkflowProcessingJobStatus
from src.common.domain.exceptions.processing import (
    CaseNotFoundError,
    WorkflowNotFoundError,
    WorkflowPipelineNotConfiguredError,
)
from src.common.domain.exceptions.storage import FileNotFoundError
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.application.processing_jobs.dispatcher import (
    WorkflowProcessingJobDispatcher,
)
from src.workflows.domain.models.pipeline import Pipeline
from src.workflows.domain.recipes import STANDARD_PIPELINE_SLUG
from src.workflows.presentation.workflows.pipeline_interpreter import (
    PipelineInterpreterWorkflow,
)


@pytest.fixture
def session():
    mock = create_autospec(spec=AsyncSession, spec_set=True, instance=True)
    mock.commit = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def temporal_client():
    mock = create_autospec(spec=TemporalClient, spec_set=True, instance=True)
    mock.start_workflow = AsyncMock(return_value=MagicMock())
    handle = MagicMock()
    handle.terminate = AsyncMock(return_value=None)
    mock.get_workflow_handle = MagicMock(return_value=handle)
    return mock


@pytest.fixture
def file_id():
    return uuid4()


@pytest.fixture
def workflow_id():
    return uuid4()


@pytest.fixture
def case_id():
    return uuid4()


@pytest.fixture
def standard_workflow(workflow_id, tenant_id):
    # E7 · F2: `workflow_type` murió — los workflows ya no se distinguen por tipo.
    return Workflow(uuid=workflow_id, tenant_id=tenant_id, name="Std workflow")


@pytest.fixture
def analysis_workflow(workflow_id, tenant_id):
    return Workflow(uuid=workflow_id, tenant_id=tenant_id, name="Analysis workflow")


@pytest.fixture
def workflow_case(case_id, workflow_id, tenant_id):
    return WorkflowCase(
        uuid=case_id,
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="Case",
    )


@pytest.fixture
def file_upload(file_id, tenant_id):
    return MagicMock(
        uuid=file_id,
        tenant_id=tenant_id,
        s3_key="files/x.pdf",
        file_name="x.pdf",
    )


def _pipeline(
    tenant_id, *, workflow_id, slug=STANDARD_PIPELINE_SLUG, current_version=1
) -> Pipeline:
    return Pipeline(
        uuid=uuid4(),
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        slug=slug,
        name="Extracción estándar",
        kind=PipelineKind.EXTRACTION,
        current_version=current_version,
    )


@pytest.fixture
def standard_pipeline(tenant_id, workflow_id):
    return _pipeline(tenant_id, workflow_id=workflow_id)


@pytest.fixture(autouse=True)
def _per_upload_case_defaults(workflow_case_repository):
    # E7 · F1 (caso universal): por defecto el caso per_upload NO existe ⇒ el
    # dispatcher lo find-or-create (find_by_external_ref→None, create echo). Los
    # tests con caso explícito (ANALYSIS) usan la rama find_by_id y no tocan esto.
    workflow_case_repository.find_by_external_ref.return_value = None
    workflow_case_repository.create.side_effect = lambda case: case


def _build_dispatcher(
    *,
    tenant_id,
    workflow_id,
    file_id,
    workflow_case_id,
    session,
    temporal_client,
    processing_job_repository,
    workflow_repository,
    workflow_case_repository,
    document_type_repository,
    file_repository,
    pipeline_repository,
    force_restart=False,
    pipeline_slug=None,
) -> WorkflowProcessingJobDispatcher:
    return WorkflowProcessingJobDispatcher(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        file_id=file_id,
        workflow_case_id=workflow_case_id,
        session=session,
        temporal_client=temporal_client,
        processing_job_repository=processing_job_repository,
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        pipeline_repository=pipeline_repository,
        task_queue="test-queue",
        force_restart=force_restart,
        pipeline_slug=pipeline_slug,
    )


@pytest.fixture
def dispatcher_for_standard(
    tenant_id,
    workflow_id,
    file_id,
    session,
    temporal_client,
    processing_job_repository,
    workflow_repository,
    workflow_case_repository,
    document_type_repository,
    file_repository,
    pipeline_repository,
):
    return _build_dispatcher(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        file_id=file_id,
        workflow_case_id=None,
        session=session,
        temporal_client=temporal_client,
        processing_job_repository=processing_job_repository,
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        pipeline_repository=pipeline_repository,
    )


@pytest.fixture
def dispatcher_for_analysis(
    tenant_id,
    workflow_id,
    file_id,
    case_id,
    session,
    temporal_client,
    processing_job_repository,
    workflow_repository,
    workflow_case_repository,
    document_type_repository,
    file_repository,
    pipeline_repository,
):
    return _build_dispatcher(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        file_id=file_id,
        workflow_case_id=case_id,
        session=session,
        temporal_client=temporal_client,
        processing_job_repository=processing_job_repository,
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        pipeline_repository=pipeline_repository,
    )


def _wire_happy_path(
    *,
    workflow_repository,
    workflow,
    processing_job_repository,
    document_type_repository,
    file_repository,
    file_upload,
    pipeline_repository,
    pipeline,
    workflow_case_repository=None,
    workflow_case=None,
):
    workflow_repository.find_by_id.return_value = workflow
    if workflow_case_repository is not None:
        workflow_case_repository.find_by_id.return_value = workflow_case
    processing_job_repository.find_by_temporal_workflow_id.return_value = None
    processing_job_repository.create.side_effect = lambda ds: ds
    document_type_repository.list_by_workflow.return_value = []
    file_repository.find_by_id.return_value = file_upload
    # ADR 0002: el workflow corre SIEMPRE su pipeline propio, resuelto por
    # `find_by_workflow(workflow_id, tenant_id)`. No hay fallback por slug.
    pipeline_repository.find_by_workflow.return_value = pipeline
    # `_resolve_scope` consulta la versión sellada; sin await_documents el scope
    # es None (full run).
    pipeline_repository.get_version.return_value = None


# --- Validation: workflow not found -------------------------------------------


async def test_execute__workflow_not_found_raises(dispatcher_for_standard, workflow_repository):
    workflow_repository.find_by_id.return_value = None

    with pytest.raises(WorkflowNotFoundError):
        await dispatcher_for_standard.execute()


# --- Validation: explicit case must belong to the workflow --------------------
# E7 · F1 (caso universal): el guard type↔caso (STANDARD sin caso / ANALYSIS con
# caso) ya no aplica — todo upload tiene caso. Solo sobrevive la validación de
# pertenencia cuando llega un ``workflow_case_id`` explícito.


async def test_execute__analysis_workflow_with_unknown_case_raises(
    dispatcher_for_analysis,
    analysis_workflow,
    workflow_repository,
    workflow_case_repository,
):
    workflow_repository.find_by_id.return_value = analysis_workflow
    workflow_case_repository.find_by_id.return_value = None

    with pytest.raises(CaseNotFoundError):
        await dispatcher_for_analysis.execute()


async def test_execute__analysis_workflow_with_case_in_other_workflow_raises(
    dispatcher_for_analysis,
    analysis_workflow,
    workflow_repository,
    workflow_case_repository,
    case_id,
    tenant_id,
):
    workflow_repository.find_by_id.return_value = analysis_workflow
    other_workflow_id = uuid4()
    workflow_case_repository.find_by_id.return_value = WorkflowCase(
        uuid=case_id,
        tenant_id=tenant_id,
        workflow_id=other_workflow_id,
        name="Other",
    )

    with pytest.raises(CaseNotFoundError):
        await dispatcher_for_analysis.execute()


# --- Validation: pipeline resolution (E1) --------------------------------------


async def test_execute__no_usable_pipeline_raises_409_before_creating_set(
    dispatcher_for_standard,
    standard_workflow,
    workflow_repository,
    pipeline_repository,
    processing_job_repository,
    temporal_client,
):
    # Arrange — el workflow no posee pipeline (ADR 0002: sin receta propia)
    workflow_repository.find_by_id.return_value = standard_workflow
    pipeline_repository.find_by_workflow.return_value = None

    # Act / Assert — falla con 409 ANTES de dejar un set huérfano o tocar Temporal
    with pytest.raises(WorkflowPipelineNotConfiguredError):
        await dispatcher_for_standard.execute()

    expect(processing_job_repository.create.call_count).to(equal(0))
    expect(temporal_client.start_workflow.await_count).to(equal(0))


async def test_execute__pipeline_without_current_version_raises_409(
    dispatcher_for_standard,
    standard_workflow,
    workflow_repository,
    pipeline_repository,
    tenant_id,
    workflow_id,
):
    workflow_repository.find_by_id.return_value = standard_workflow
    pipeline_repository.find_by_workflow.return_value = _pipeline(
        tenant_id, workflow_id=workflow_id, current_version=None
    )

    with pytest.raises(WorkflowPipelineNotConfiguredError):
        await dispatcher_for_standard.execute()


async def test_execute__resolves_pipeline_owned_by_workflow(
    dispatcher_for_standard,
    standard_workflow,
    workflow_repository,
    processing_job_repository,
    document_type_repository,
    file_repository,
    file_upload,
    pipeline_repository,
    temporal_client,
    tenant_id,
    workflow_id,
):
    # Arrange — ADR 0002: el workflow es dueño 1:1 de su receta propia
    owned_pipeline = _pipeline(
        tenant_id, workflow_id=workflow_id, slug="custom-recipe", current_version=5
    )
    _wire_happy_path(
        workflow_repository=workflow_repository,
        workflow=standard_workflow,
        processing_job_repository=processing_job_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        file_upload=file_upload,
        pipeline_repository=pipeline_repository,
        pipeline=owned_pipeline,
    )

    # Act
    await dispatcher_for_standard.execute()

    # Assert — sella pipeline_id + current_version vía find_by_workflow
    pipeline_repository.find_by_workflow.assert_awaited_once_with(workflow_id, tenant_id)
    run_input = temporal_client.start_workflow.call_args.args[1]
    expect(run_input.pipeline_id).to(equal(owned_pipeline.uuid))
    expect(run_input.version).to(equal(5))


async def test_execute__explicit_pipeline_slug_is_ignored(
    tenant_id,
    workflow_id,
    file_id,
    session,
    temporal_client,
    processing_job_repository,
    workflow_repository,
    workflow_case_repository,
    document_type_repository,
    file_repository,
    pipeline_repository,
    standard_workflow,
    file_upload,
):
    # Arrange — ADR 0002: el override por slug (M2M deprecado) se IGNORA; el
    # workflow corre SIEMPRE su pipeline propio resuelto por find_by_workflow.
    dispatcher = _build_dispatcher(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        file_id=file_id,
        workflow_case_id=None,
        session=session,
        temporal_client=temporal_client,
        processing_job_repository=processing_job_repository,
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        pipeline_repository=pipeline_repository,
        pipeline_slug="custom-recipe",
    )
    owned = _pipeline(
        tenant_id, workflow_id=workflow_id, slug="standard-extraction", current_version=3
    )
    _wire_happy_path(
        workflow_repository=workflow_repository,
        workflow=standard_workflow,
        processing_job_repository=processing_job_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        file_upload=file_upload,
        pipeline_repository=pipeline_repository,
        pipeline=owned,
    )

    # Act
    await dispatcher.execute()

    # Assert — el slug se ignora; sella el pipeline propio del workflow
    pipeline_repository.find_by_workflow.assert_awaited_once_with(workflow_id, tenant_id)
    run_input = temporal_client.start_workflow.call_args.args[1]
    expect(run_input.pipeline_id).to(equal(owned.uuid))
    expect(run_input.version).to(equal(3))


# --- File-not-found error path ------------------------------------------------


async def test_execute__missing_file_raises(
    dispatcher_for_standard,
    standard_workflow,
    workflow_repository,
    processing_job_repository,
    file_repository,
    pipeline_repository,
    standard_pipeline,
):
    workflow_repository.find_by_id.return_value = standard_workflow
    pipeline_repository.find_by_workflow.return_value = standard_pipeline
    processing_job_repository.find_by_temporal_workflow_id.return_value = None
    processing_job_repository.create.side_effect = lambda ds: ds
    file_repository.find_by_id.return_value = None

    with pytest.raises(FileNotFoundError):
        await dispatcher_for_standard.execute()


# --- Happy path: STANDARD -----------------------------------------------------


async def test_execute__standard_finds_or_creates_per_upload_case(
    dispatcher_for_standard,
    standard_workflow,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_type_repository,
    file_repository,
    file_upload,
    pipeline_repository,
    standard_pipeline,
    file_id,
):
    # E7 · F1 (caso universal): un upload STANDARD (sin workflow_case_id) ahora
    # find-or-create un caso per_upload; el set queda colgado de él.
    _wire_happy_path(
        workflow_repository=workflow_repository,
        workflow=standard_workflow,
        processing_job_repository=processing_job_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        file_upload=file_upload,
        pipeline_repository=pipeline_repository,
        pipeline=standard_pipeline,
    )

    result = await dispatcher_for_standard.execute()

    expect(result).to(be_a(WorkflowProcessingJob))
    expect(result.status).to(equal(WorkflowProcessingJobStatus.PENDING))
    # find-or-create idempotente por archivo, nombrado con el file_name (+ sufijo).
    created_case = workflow_case_repository.create.call_args.args[0]
    expect(created_case.external_ref).to(equal(f"upload:{file_id.hex}"))
    expect(created_case.name).to(contain(file_upload.file_name))
    persisted_set = processing_job_repository.create.call_args.args[0]
    expect(persisted_set.workflow_case_id).to(equal(created_case.uuid))


async def test_execute__starts_temporal_workflow_with_correct_id(
    dispatcher_for_standard,
    standard_workflow,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_type_repository,
    file_repository,
    file_upload,
    pipeline_repository,
    standard_pipeline,
    temporal_client,
    file_id,
):
    _wire_happy_path(
        workflow_repository=workflow_repository,
        workflow=standard_workflow,
        processing_job_repository=processing_job_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        file_upload=file_upload,
        pipeline_repository=pipeline_repository,
        pipeline=standard_pipeline,
    )

    result = await dispatcher_for_standard.execute()

    expect(temporal_client.start_workflow.await_count).to(equal(1))
    call_kwargs = temporal_client.start_workflow.call_args.kwargs
    expect(call_kwargs["id"]).to(equal(result.temporal_workflow_id))
    expect(call_kwargs["task_queue"]).to(equal("test-queue"))
    # E7 · F1: el temporal_workflow_id se namespacea por el caso per_upload (que
    # cuelga el upload), no por el workflow.
    created_case = workflow_case_repository.create.call_args.args[0]
    expect(result.temporal_workflow_id).to(contain(created_case.uuid.hex))
    expect(result.temporal_workflow_id).to(contain(file_id.hex))


async def test_execute__starts_interpreter_with_sealed_pipeline_run_input(
    dispatcher_for_standard,
    standard_workflow,
    workflow_repository,
    processing_job_repository,
    document_type_repository,
    file_repository,
    file_upload,
    pipeline_repository,
    standard_pipeline,
    temporal_client,
    workflow_id,
    file_id,
    tenant_id,
):
    """Tras el cutover E1 todo upload corre por ``PipelineInterpreterWorkflow``
    con la receta sellada (pipeline_id + version) en el ``PipelineRunInput``."""
    _wire_happy_path(
        workflow_repository=workflow_repository,
        workflow=standard_workflow,
        processing_job_repository=processing_job_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        file_upload=file_upload,
        pipeline_repository=pipeline_repository,
        pipeline=standard_pipeline,
    )

    result = await dispatcher_for_standard.execute()

    call_args = temporal_client.start_workflow.call_args
    expect(call_args.args[0]).to(be(PipelineInterpreterWorkflow.run))
    run_input = call_args.args[1]
    expect(run_input).to(be_a(PipelineRunInput))
    expect(run_input.pipeline_id).to(equal(standard_pipeline.uuid))
    expect(run_input.version).to(equal(standard_pipeline.current_version))
    # Un run de upload completo arranca de cero: sin artefactos pre-sembrados.
    expect(run_input.initial_artifacts).to(equal({}))
    expect(run_input.starting_seq).to(equal(0))
    document = run_input.document
    expect(document.job_id).to(equal(result.temporal_workflow_id))
    expect(document.object_key).to(equal("files/x.pdf"))
    expect(document.workflow_id).to(equal(workflow_id))
    expect(document.tenant_id).to(equal(tenant_id))
    expect(document.file_id).to(equal(file_id))
    expect(document.processing_job_uuid).to(equal(result.uuid))
    expect(document.persist).to(equal(True))


async def test_execute__commits_session_before_starting_temporal(
    dispatcher_for_standard,
    standard_workflow,
    workflow_repository,
    processing_job_repository,
    document_type_repository,
    file_repository,
    file_upload,
    pipeline_repository,
    standard_pipeline,
    session,
    temporal_client,
):
    _wire_happy_path(
        workflow_repository=workflow_repository,
        workflow=standard_workflow,
        processing_job_repository=processing_job_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        file_upload=file_upload,
        pipeline_repository=pipeline_repository,
        pipeline=standard_pipeline,
    )
    call_order: list[str] = []
    session.commit.side_effect = lambda: call_order.append("commit")

    async def _start_workflow(*args, **kwargs):
        call_order.append("start_workflow")
        return MagicMock()

    temporal_client.start_workflow.side_effect = _start_workflow

    await dispatcher_for_standard.execute()

    expect(call_order).to(equal(["commit", "start_workflow"]))


# --- Happy path: ANALYSIS -----------------------------------------------------


async def test_execute__analysis_creates_set_with_workflow_case_id(
    dispatcher_for_analysis,
    analysis_workflow,
    workflow_case,
    workflow_repository,
    workflow_case_repository,
    processing_job_repository,
    document_type_repository,
    file_repository,
    file_upload,
    pipeline_repository,
    standard_pipeline,
    case_id,
):
    _wire_happy_path(
        workflow_repository=workflow_repository,
        workflow=analysis_workflow,
        processing_job_repository=processing_job_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        file_upload=file_upload,
        pipeline_repository=pipeline_repository,
        pipeline=standard_pipeline,
        workflow_case_repository=workflow_case_repository,
        workflow_case=workflow_case,
    )

    await dispatcher_for_analysis.execute()

    persisted_set = processing_job_repository.create.call_args.args[0]
    expect(persisted_set.workflow_case_id).to(equal(case_id))


# --- Idempotency: existing in-progress / terminal sets ------------------------


@pytest.mark.parametrize(
    "current_status",
    [
        WorkflowProcessingJobStatus.RUNNING,
        WorkflowProcessingJobStatus.PROCESSING,
        WorkflowProcessingJobStatus.COMPLETED,
        WorkflowProcessingJobStatus.PARTIAL,
    ],
)
async def test_execute__idempotent_when_set_in_active_or_completed_state(
    dispatcher_for_standard,
    standard_workflow,
    workflow_repository,
    processing_job_repository,
    file_repository,
    pipeline_repository,
    standard_pipeline,
    temporal_client,
    tenant_id,
    workflow_id,
    file_id,
    current_status,
):
    workflow_repository.find_by_id.return_value = standard_workflow
    pipeline_repository.find_by_workflow.return_value = standard_pipeline
    existing_set = WorkflowProcessingJob(
        uuid=uuid4(),
        temporal_workflow_id="CASE#abc_FILE#def",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        file_id=file_id,
        status=current_status,
    )
    processing_job_repository.find_by_temporal_workflow_id.return_value = existing_set

    result = await dispatcher_for_standard.execute()

    expect(result.status).to(equal(current_status))
    # El invariante del skip idempotente es NO re-despachar Temporal (E7 · F1: el
    # archivo se carga temprano para nombrar el caso per_upload, así que ya no se
    # exige await_count==0 de file_repository).
    expect(temporal_client.start_workflow.await_count).to(equal(0))


# --- Recovery from FAILED -----------------------------------------------------


async def test_execute__failed_set_is_reset_and_redispatched(
    dispatcher_for_standard,
    standard_workflow,
    workflow_repository,
    processing_job_repository,
    document_type_repository,
    file_repository,
    file_upload,
    pipeline_repository,
    standard_pipeline,
    temporal_client,
    tenant_id,
    workflow_id,
    file_id,
):
    workflow_repository.find_by_id.return_value = standard_workflow
    pipeline_repository.find_by_workflow.return_value = standard_pipeline
    pipeline_repository.get_version.return_value = None
    failed_set = WorkflowProcessingJob(
        uuid=uuid4(),
        temporal_workflow_id="CASE#abc_FILE#def",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        file_id=file_id,
        status=WorkflowProcessingJobStatus.FAILED,
    )
    processing_job_repository.find_by_temporal_workflow_id.return_value = failed_set
    processing_job_repository.reset_to_pending.return_value = None
    document_type_repository.list_by_workflow.return_value = []
    file_repository.find_by_id.return_value = file_upload

    result = await dispatcher_for_standard.execute()

    expect(result.status).to(equal(WorkflowProcessingJobStatus.PENDING))
    expect(processing_job_repository.reset_to_pending.await_count).to(equal(1))
    expect(temporal_client.start_workflow.await_count).to(equal(1))


# --- Force restart ------------------------------------------------------------


async def test_execute__force_restart_terminates_existing_temporal_workflow(
    tenant_id,
    workflow_id,
    file_id,
    session,
    temporal_client,
    processing_job_repository,
    workflow_repository,
    workflow_case_repository,
    document_type_repository,
    file_repository,
    pipeline_repository,
    standard_workflow,
    standard_pipeline,
    file_upload,
):
    dispatcher = _build_dispatcher(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        file_id=file_id,
        workflow_case_id=None,
        session=session,
        temporal_client=temporal_client,
        processing_job_repository=processing_job_repository,
        workflow_repository=workflow_repository,
        workflow_case_repository=workflow_case_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        pipeline_repository=pipeline_repository,
        force_restart=True,
    )
    workflow_repository.find_by_id.return_value = standard_workflow
    pipeline_repository.find_by_workflow.return_value = standard_pipeline
    pipeline_repository.get_version.return_value = None
    existing_set = WorkflowProcessingJob(
        uuid=uuid4(),
        temporal_workflow_id="CASE#abc_FILE#def",
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        file_id=file_id,
        status=WorkflowProcessingJobStatus.RUNNING,
    )
    processing_job_repository.find_by_temporal_workflow_id.return_value = existing_set
    processing_job_repository.reset_to_pending.return_value = None
    document_type_repository.list_by_workflow.return_value = []
    file_repository.find_by_id.return_value = file_upload

    await dispatcher.execute()

    handle = temporal_client.get_workflow_handle.return_value
    expect(handle.terminate.await_count).to(equal(1))
    expect(temporal_client.start_workflow.await_count).to(equal(1))


# --- WorkflowAlreadyStartedError tolerance ------------------------------------


async def test_execute__swallows_workflow_already_started(
    dispatcher_for_standard,
    standard_workflow,
    workflow_repository,
    processing_job_repository,
    document_type_repository,
    file_repository,
    file_upload,
    pipeline_repository,
    standard_pipeline,
    temporal_client,
):
    _wire_happy_path(
        workflow_repository=workflow_repository,
        workflow=standard_workflow,
        processing_job_repository=processing_job_repository,
        document_type_repository=document_type_repository,
        file_repository=file_repository,
        file_upload=file_upload,
        pipeline_repository=pipeline_repository,
        pipeline=standard_pipeline,
    )
    temporal_client.start_workflow.side_effect = WorkflowAlreadyStartedError(
        "already started", "PipelineInterpreterWorkflow"
    )

    result = await dispatcher_for_standard.execute()

    expect(result.status).to(equal(WorkflowProcessingJobStatus.PENDING))
