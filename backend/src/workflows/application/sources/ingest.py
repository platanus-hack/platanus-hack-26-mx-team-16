"""Ingest one file through a configurable Source → run its pipeline (F8 · W2).

``POST /v1/ingest/{token}`` resolves the route token to a Source, authenticates
per its ``auth_mode``, resolves the workflow's active pipeline, and dispatches the
generic ``PipelineInterpreterWorkflow`` (sealing ``pipeline_id`` + ``version``).
The file is already in S3 by the time we get here (the endpoint streamed the
upload); this use-case owns resolution, auth and dispatch only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from temporalio.client import Client

from temporalio.client import Client as TemporalClient

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.analysis_run_processing import (
    DispatchCaseEventInput,
)
from src.common.domain.entities.workflows.document_processing import DocumentProcessingInput
from src.common.domain.entities.workflows.pipeline_run import PipelineRunInput
from src.common.domain.enums.webhooks import WebhookEventType
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.connections.domain.exceptions import (
    IngestCaseNotAllowedError,
    IngestCaseNotFoundError,
    SourceAuthFailedError,
    SourceNotFoundError,
    SourcePipelineNotConfiguredError,
)
from src.connections.domain.repositories.workflow_source import WorkflowSourceRepository
from src.connections.domain.services.source_auth import verify_source_auth
from src.workflows.application.document_processing.input_builder import (
    doctype_to_temporal_dict,
)
from src.workflows.application.workflow_cases.case_run_starter import EnsureCaseRunStarted
from src.workflows.application.workflow_cases.m2m import FindOrCreateCaseM2M
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.presentation.workflows.pipeline_interpreter import (
    PipelineInterpreterWorkflow,
)

logger = get_logger(__name__)


@dataclass
class IngestViaSource(UseCase):
    route_token: str
    object_key: str
    file_name: str
    source_repository: WorkflowSourceRepository
    pipeline_repository: PipelineRepository
    temporal_client: Client
    task_queue: str
    file_id: UUID
    processing_job_uuid: UUID
    document_types: list[dict] = field(default_factory=list)
    # E5: classify necesita el catálogo de doctypes del workflow para etiquetar;
    # sin él, el LLM inventa tipos y los docs quedan sin document_type_id.
    document_type_repository: DocumentTypeRepository | None = None
    # E4 · spec source_webhooks §7.3: caso resuelto por el endpoint — viaja en
    # el DocumentProcessingInput hasta PERSIST_CLASSIFIED_DOCS, igual que los
    # uploads UI a caso (los WorkflowDocument quedan con workflow_case_id).
    case_id: UUID | None = None
    # Auth context extracted from the request by the endpoint.
    api_key: str | None = None
    signature: str | None = None
    timestamp: int | None = None
    body: str | None = None
    now: int | None = None
    # E6 · W5: native channels arrive verified by the provider's own signature
    # (checked at the channel endpoint). Skip the Svix-style auth re-check; the
    # API ingest endpoint never sets this, so its auth is unchanged.
    pre_authenticated: bool = False
    # E6 · W5: override the per-attachment job id (channel messages key the job
    # on the provider message id + attachment index, not the file id).
    job_id_override: str | None = None
    # E6 · W5: extra MIMEs allowed for this ingest (channel audio voice notes).
    extra_allowed_mimes: list[str] = field(default_factory=list)

    async def execute(self) -> str:
        source = await self.source_repository.find_by_route_token(self.route_token)
        if source is None or not source.enabled:
            raise SourceNotFoundError(self.route_token)

        if not self.pre_authenticated and not verify_source_auth(
            source,
            api_key=self.api_key,
            signature=self.signature,
            timestamp=self.timestamp,
            body=self.body,
            now=self.now,
        ):
            raise SourceAuthFailedError()

        # ADR 0002: la fuente corre el pipeline PROPIO de su workflow (sin catálogo
        # tenant por slug). ``pipeline_slug`` en source.config quedó deprecado.
        pipeline = await self.pipeline_repository.find_by_workflow(source.workflow_id, source.tenant_id)
        if pipeline is None or pipeline.current_version is None:
            raise SourcePipelineNotConfiguredError()

        document_types = self.document_types
        if not document_types and self.document_type_repository is not None:
            doctypes = await self.document_type_repository.list_by_workflow(
                source.workflow_id, source.tenant_id
            )
            document_types = [doctype_to_temporal_dict(dt) for dt in doctypes]

        job_id = self.job_id_override or f"SRC#{source.route_token}_FILE#{self.file_id.hex[:12]}"
        await self.temporal_client.start_workflow(
            PipelineInterpreterWorkflow.run,
            PipelineRunInput(
                pipeline_id=pipeline.uuid,
                version=pipeline.current_version,
                # E5: con caso, el run del archivo es document-scope — la cola
                # del caso (await_documents en adelante) vive en el CASE#
                # durable que ResolveIngestCase ya arrancó. Sin scope, una
                # receta con await_documents se quedaría esperando señales
                # inline en este SRC# (cazado en el E2E Caso 3).
                scope="document" if self.case_id is not None else None,
                document=DocumentProcessingInput(
                    object_key=self.object_key,
                    document_types=document_types,
                    job_id=job_id,
                    case_id=self.case_id,
                    workflow_id=source.workflow_id,
                    tenant_id=source.tenant_id,
                    file_id=self.file_id,
                    file_name=self.file_name,
                    processing_job_uuid=self.processing_job_uuid,
                    persist=True,
                ),
            ),
            id=job_id,
            task_queue=self.task_queue,
        )
        logger.info("source.ingest_dispatched", route_token=source.route_token, job_id=job_id)
        return job_id


@dataclass
class ResolveIngestCaseResult:
    case: WorkflowCase | None
    created: bool


@dataclass
class ResolveIngestCase(UseCase):
    """Vínculo ingest → caso (E4 · spec source_webhooks §7.2/§7.3).

    Orden de resolución del spec: (1) ``caseId`` — el case debe existir en el
    workflow del source ⇒ si no, 400 ``ingest.CaseNotFound``; (2) ``caseName``
    — find-or-create (en la re-arquitectura el agrupador del ERP es
    ``external_ref``, único por workflow ⇒ delega en :class:`FindOrCreateCaseM2M`
    con su retry de carrera por ``IntegrityError``); (3) ninguno ⇒ set anónimo
    (comportamiento actual — el caller no nos invoca o recibe ``case=None``).

    Workflow no-ANALYSIS con referencia de caso ⇒ 400 ``ingest.CaseNotAllowed``
    (spec §7.2, validación previa). Tras crear/encontrar: ``case.created`` SOLO
    en creación real (vía dispatcher inyectado, best-effort) y
    :class:`EnsureCaseRunStarted` idempotente (no-op sin ``await_documents``).
    """

    tenant_id: UUID
    workflow_id: UUID
    workflow_repository: WorkflowRepository
    case_repository: WorkflowCaseRepository
    pipeline_repository: PipelineRepository
    temporal_client: TemporalClient
    task_queue: str
    case_id: UUID | None = None
    case_name: str | None = None  # spec `caseName` ≡ external_ref (re-arch)
    # Objeto con ``dispatch(DispatchCaseEventInput)`` (CaseEventDispatcher).
    case_event_dispatcher: object | None = None

    async def execute(self) -> ResolveIngestCaseResult:
        if self.case_id is None and not self.case_name:
            return ResolveIngestCaseResult(case=None, created=False)

        # E7 · F2 (caso universal): la ingesta con caso ya no exige ANALYSIS —
        # todo workflow tiene casos. Solo falla si el workflow no existe.
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise IngestCaseNotAllowedError()

        if self.case_id is not None:
            case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
            if case is None or case.workflow_id != self.workflow_id:
                raise IngestCaseNotFoundError(str(self.case_id))
            created = False
        else:
            result = await FindOrCreateCaseM2M(
                tenant_id=self.tenant_id,
                workflow_id=self.workflow_id,
                external_ref=self.case_name,
                workflow_repository=self.workflow_repository,
                case_repository=self.case_repository,
                pipeline_repository=self.pipeline_repository,
            ).execute()
            case, created = result.case, result.created

        if created and self.case_event_dispatcher is not None:
            # Evento solo en creación real (idempotencia); jamás rompe la ingesta.
            try:
                await self.case_event_dispatcher.dispatch(
                    DispatchCaseEventInput(
                        tenant_id=self.tenant_id,
                        workflow_id=case.workflow_id,
                        case_id=case.uuid,
                        event_type=WebhookEventType.CASE_CREATED.value,
                        error={"externalRef": case.external_ref, "name": case.name},
                    )
                )
            except Exception:  # noqa: BLE001
                logger.exception("ingest.case_created_dispatch_failed", case_id=str(case.uuid))

        # Tras crear/encontrar: CASE# idempotente (WorkflowAlreadyStarted se
        # ignora dentro; no-op si la receta no tiene await_documents).
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
        except Exception:  # noqa: BLE001
            logger.exception("ingest.case_run_ensure_failed", case_id=str(case.uuid))

        return ResolveIngestCaseResult(case=case, created=created)
