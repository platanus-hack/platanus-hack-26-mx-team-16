"""Use cases del plano 2 de la API pública: el expediente (E3 · plan §4.4).

- :class:`FindOrCreateCaseM2M` — ``POST /v1/cases``: find-or-create por
  ``external_ref`` (único por workflow); el workflow es OBLIGATORIO (decisión
  E1) y debe ser ANALYSIS; ``pipeline`` (slug) opcional queda sellado en el
  caso para los runs data-only.
- :class:`SubmitCaseData` — ``POST /v1/cases/{id}/data``: materializa el
  payload como documento virtual ``EXTERNAL_DATA`` y AUTO-ARRANCA el run del
  caso (receta ``case.pipeline_id`` → ``data-analysis@v1``). En E3 el run
  data-only corre sin document set (sin SSE); la observabilidad es
  ``GET /v1/cases/{id}`` + webhooks ``case.*``. Cada envío crea un documento
  nuevo y dispara un run nuevo — la fase ``analyze`` serializa concurrentes.
- :class:`GetCaseM2M` / :class:`GetCaseOutputM2M` — lectura compuesta (estado +
  documentos + runs) y el output del último run COMPLETED.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from temporalio.client import Client as TemporalClient

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.document_processing import DocumentProcessingInput
from src.common.domain.entities.workflows.pipeline_run import PipelineRunInput
from src.common.domain.enums.workflow_rules import WorkflowAnalysisRunStatus
from src.common.domain.enums.workflows import WorkflowDocumentSource
from src.common.domain.exceptions._base import DomainError
from src.common.domain.exceptions.processing import (
    CaseNotFoundError,
    WorkflowNotFoundError,
    WorkflowPipelineNotConfiguredError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.application.workflow_cases.case_run_starter import (
    CASE_DOCS_CHANGED_SIGNAL,
    EnsureCaseRunStarted,
    signal_case_run,
)
from src.workflows.application.workflow_cases.recipe_resolver import (
    recipe_has_await_documents,
    resolve_case_recipe,
)
from src.workflows.application.pipelines.entry_points import EntryPoint, select_phases
from src.workflows.application.workflow_documents.virtual_creator import CreateVirtualDocument
from src.workflows.domain.repositories.case_event import CaseEventRepository
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.domain.run_summary.repositories.run_summary import (
    WorkflowAnalysisRunSummaryRepository,
)

logger = get_logger(__name__)


class CaseOutputNotReadyError(DomainError):
    def __init__(self, case_id: str = ""):
        super().__init__(
            code="case.output_not_ready",
            message="The case has no completed analysis run with output yet.",
            status_code=404,
            context={"case_id": case_id},
        )


class PipelineSlugNotFoundError(DomainError):
    def __init__(self, slug: str = ""):
        super().__init__(
            code="pipeline.not_found",
            message=f"Pipeline slug not found for this tenant: {slug}",
            status_code=404,
        )


@dataclass
class FindOrCreateCaseResult:
    case: WorkflowCase
    created: bool


@dataclass
class FindOrCreateCaseM2M(UseCase):
    tenant_id: UUID
    workflow_id: UUID
    workflow_repository: WorkflowRepository
    case_repository: WorkflowCaseRepository
    pipeline_repository: PipelineRepository
    external_ref: str | None = None
    pipeline_slug: str | None = None
    name: str | None = None

    async def execute(self) -> FindOrCreateCaseResult:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))
        # E7 · F1 (caso universal): todo workflow tiene casos — ya no se exige
        # ANALYSIS. La capacidad real (¿corre análisis?, ¿acepta datos?) la deriva
        # el pipeline, no ``workflow_type`` (que muere en F2).

        # ADR 0002: el caso corre el pipeline PROPIO de su workflow; ya no se
        # elige por slug de un catálogo tenant. ``pipeline_slug`` (param M2M)
        # quedó deprecado y se ignora — ``resolve_case_recipe`` resuelve el
        # pipeline del workflow.
        pipeline_id: UUID | None = None

        if self.external_ref:
            existing = await self.case_repository.find_by_external_ref(
                self.workflow_id, self.external_ref, self.tenant_id
            )
            if existing is not None:
                return FindOrCreateCaseResult(case=existing, created=False)

        case = WorkflowCase(
            uuid=uuid4(),
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            name=self.name or self.external_ref or f"API case {uuid4().hex[:8]}",
            external_ref=self.external_ref,
            pipeline_id=pipeline_id,
        )
        try:
            created = await self.case_repository.create(case)
        except IntegrityError:
            # Carrera del find-or-create sobre el unique (workflow, external_ref):
            # otro request lo creó entre el find y el insert — adoptarlo.
            if not self.external_ref:
                raise
            existing = await self.case_repository.find_by_external_ref(
                self.workflow_id, self.external_ref, self.tenant_id
            )
            if existing is None:
                raise
            return FindOrCreateCaseResult(case=existing, created=False)
        return FindOrCreateCaseResult(case=created, created=True)


@dataclass
class SubmitCaseDataResult:
    document: WorkflowDocument
    job_id: str


@dataclass
class SubmitCaseData(UseCase):
    tenant_id: UUID
    case_id: UUID
    doc_type_slug: str
    payload: dict
    case_repository: WorkflowCaseRepository
    document_repository: WorkflowDocumentRepository
    document_type_repository: DocumentTypeRepository
    pipeline_repository: PipelineRepository
    temporal_client: TemporalClient
    task_queue: str
    auto_start: bool = True
    workflow_repository: WorkflowRepository | None = None

    async def execute(self) -> SubmitCaseDataResult:
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if case is None:
            raise CaseNotFoundError(str(self.case_id))

        document = await CreateVirtualDocument(
            tenant_id=self.tenant_id,
            workflow_id=case.workflow_id,
            case_id=case.uuid,
            doc_type_slug=self.doc_type_slug,
            payload=self.payload,
            source=WorkflowDocumentSource.EXTERNAL_DATA,
            document_repository=self.document_repository,
            document_type_repository=self.document_type_repository,
        ).execute()

        # E4 · diseño §3: con await_documents en la receta, el caso tiene su run
        # CASE# — el dato nuevo solo re-evalúa completitud (señal best-effort).
        # Sin await_documents se conserva el comportamiento E3 (run DATA#).
        version = await resolve_case_recipe(
            case,
            self.tenant_id,
            pipeline_repository=self.pipeline_repository,
            workflow_repository=self.workflow_repository,
        )
        if recipe_has_await_documents(version):
            try:
                await EnsureCaseRunStarted(
                    tenant_id=self.tenant_id,
                    case_id=case.uuid,
                    case_repository=self.case_repository,
                    pipeline_repository=self.pipeline_repository,
                    workflow_repository=self.workflow_repository,
                    temporal_client=self.temporal_client,
                    task_queue=self.task_queue,
                ).execute()
            except Exception:  # noqa: BLE001 — el dato ya está persistido
                logger.exception("case.data_case_run_ensure_failed", case_id=str(case.uuid))
            await signal_case_run(self.temporal_client, case.uuid, CASE_DOCS_CHANGED_SIGNAL)
            return SubmitCaseDataResult(document=document, job_id="")

        job_id = ""
        if self.auto_start:
            job_id = await self._start_data_run(case)
        return SubmitCaseDataResult(document=document, job_id=job_id)

    async def _start_data_run(self, case: WorkflowCase) -> str:
        # ADR 0002 · §3.6: el run data-only corre el pipeline PROPIO del workflow
        # con ``entry_point="data"`` (sub-segmento desde la primera ``analyze``).
        pipeline = await self.pipeline_repository.find_by_workflow(case.workflow_id, self.tenant_id)
        if pipeline is None or pipeline.current_version is None:
            raise WorkflowPipelineNotConfiguredError(str(case.workflow_id))
        version = await self.pipeline_repository.get_version(pipeline.uuid, pipeline.current_version)
        # zanjado #2: POST /v1/cases/{id}/data sobre un pipeline SIN fase
        # ``analyze`` es un error de configuración (409), no un dispatch al vacío.
        if version is None or not select_phases(version.phases, EntryPoint.DATA):
            raise WorkflowPipelineNotConfiguredError(str(case.workflow_id))

        from src.workflows.presentation.workflows.pipeline_interpreter import (
            PipelineInterpreterWorkflow,
        )

        # Run data-only (E3): sin archivo ni document set — los checkpoints
        # hacen early-return (sin SSE); la fase analyze serializa concurrentes.
        job_id = f"DATA#{case.uuid.hex}_{uuid4().hex[:12]}"
        await self.temporal_client.start_workflow(
            PipelineInterpreterWorkflow.run,
            PipelineRunInput(
                pipeline_id=pipeline.uuid,
                version=pipeline.current_version,
                entry_point="data",
                document=DocumentProcessingInput(
                    object_key="",
                    document_types=[],
                    job_id=job_id,
                    case_id=case.uuid,
                    workflow_id=case.workflow_id,
                    tenant_id=self.tenant_id,
                    persist=True,
                ),
            ),
            id=job_id,
            task_queue=self.task_queue,
        )
        logger.info("case.data_run_started", case_id=str(case.uuid), job_id=job_id)
        return job_id


@dataclass
class CaseAggregate:
    case: WorkflowCase
    documents: list[WorkflowDocument]
    runs: list
    latest_summary: object | None
    timeline: list = field(default_factory=list)  # case_events desc (límite 50, E4)
    # E5 · fan-out: {status: n} de los children (vacío si no es padre).
    children_by_status: dict[str, int] = field(default_factory=dict)


@dataclass
class GetCaseM2M(UseCase):
    tenant_id: UUID
    case_id: UUID
    case_repository: WorkflowCaseRepository
    document_repository: WorkflowDocumentRepository
    run_repository: WorkflowAnalysisRunRepository
    summary_repository: WorkflowAnalysisRunSummaryRepository
    case_event_repository: CaseEventRepository | None = None

    async def execute(self) -> CaseAggregate:
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if case is None:
            raise CaseNotFoundError(str(self.case_id))
        documents = await self.document_repository.list_by_case(self.case_id, self.tenant_id)
        runs = await self.run_repository.list_by_case(self.case_id, self.tenant_id)
        latest_summary = None
        for run in runs:
            if run.status == WorkflowAnalysisRunStatus.COMPLETED:
                latest_summary = await self.summary_repository.find_by_run(run.uuid, self.tenant_id)
                if latest_summary is not None:
                    break
        timeline: list = []
        if self.case_event_repository is not None:
            timeline = await self.case_event_repository.list_by_case(
                self.case_id, self.tenant_id, limit=50, desc=True
            )
        children_by_status = await self.case_repository.count_children_by_status(
            self.case_id, self.tenant_id
        )
        return CaseAggregate(
            case=case,
            documents=documents,
            runs=runs,
            latest_summary=latest_summary,
            timeline=timeline,
            children_by_status=children_by_status or {},
        )


@dataclass
class GetCaseOutputM2M(UseCase):
    tenant_id: UUID
    case_id: UUID
    case_repository: WorkflowCaseRepository
    run_repository: WorkflowAnalysisRunRepository
    summary_repository: WorkflowAnalysisRunSummaryRepository

    async def execute(self):
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if case is None:
            raise CaseNotFoundError(str(self.case_id))
        runs = await self.run_repository.list_by_case(self.case_id, self.tenant_id)
        for run in runs:
            if run.status != WorkflowAnalysisRunStatus.COMPLETED:
                continue
            summary = await self.summary_repository.find_by_run(run.uuid, self.tenant_id)
            if summary is not None:
                return run, summary
        raise CaseOutputNotReadyError(str(self.case_id))