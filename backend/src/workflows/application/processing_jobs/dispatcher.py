"""Unified dispatcher for the bulk file-extraction Temporal workflow.

E7 · F1 (caso universal): **every** upload hangs off a WorkflowCase. If the
caller provides a ``workflow_case_id`` (ANALYSIS expedientes, re-extraction) it
is validated for ownership; otherwise a ``per_upload`` case is find-or-created
(idempotent per file) before the ``workflow_processing_job`` row. The old
``workflow_type``↔``workflow_case_id`` guard is gone — the document set is now
purely the technical run-record of one file, the case is the business
container. Straight-through recipes (no case-scope phases) get closed by
``finalize`` (RECEIVING→PROCESSING→COMPLETED).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client as TemporalClient
from temporalio.exceptions import WorkflowAlreadyStartedError

from src.common.domain.interfaces.use_case import UseCase
from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.document_processing import (
    DocumentProcessingInput,
)
from src.common.domain.entities.workflows.pipeline_run import PipelineRunInput
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.enums.workflows import (
    WorkflowProcessingJobStatus,
    WorkflowProcessingJobTrigger,
)
from src.common.domain.exceptions.processing import (
    CaseNotFoundError,
    WorkflowNotFoundError,
)
from src.common.domain.exceptions.storage import FileNotFoundError
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.storage.domain.repositories.file_repository import FileRepository
from src.workflows.application.document_processing.input_builder import (
    build_job_id,
    doctype_to_temporal_dict,
)
from src.workflows.application.workflow_cases.m2m import FindOrCreateCaseM2M
from src.workflows.application.document_types.lister import DocumentTypeLister
from src.workflows.application.pipelines.resolver import resolve_workflow_pipeline
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)
from src.workflows.presentation.workflows.pipeline_interpreter import (
    PipelineInterpreterWorkflow,
)

logger = get_logger(__name__)


@dataclass
class WorkflowProcessingJobDispatcher(UseCase):
    """Validate inputs, persist the document set, start the Temporal workflow."""

    tenant_id: UUID
    workflow_id: UUID
    file_id: UUID
    workflow_case_id: UUID | None
    session: AsyncSession
    temporal_client: TemporalClient
    processing_job_repository: WorkflowProcessingJobRepository
    workflow_repository: WorkflowRepository
    workflow_case_repository: WorkflowCaseRepository
    document_type_repository: DocumentTypeRepository
    file_repository: FileRepository
    pipeline_repository: PipelineRepository
    task_queue: str
    force_restart: bool = False
    created_by_id: UUID | None = None
    trigger: WorkflowProcessingJobTrigger = WorkflowProcessingJobTrigger.USER
    # Override explícito de receta (POST /v1/extract?pipeline=<slug>); sin él
    # se resuelve binding del workflow → standard-extraction del tenant.
    pipeline_slug: str | None = None

    async def execute(self) -> WorkflowProcessingJob:
        workflow = await self._load_workflow()

        # Receta sellada ANTES de tocar nada: sin pipeline utilizable el dispatch
        # falla con 409 sin dejar un set NI un caso huérfano (E1 · E7·F1).
        resolved = await self._resolve_pipeline(workflow)

        # E7 · F1 (caso universal): todo upload cuelga de un caso. Cargamos el
        # archivo (para nombrar el caso y fallar rápido si no existe) y
        # garantizamos el caso ANTES de sellar el temporal_workflow_id, que lo
        # namespacea (``build_job_id(case_id or workflow_id, file_id)``).
        file_upload = await self.file_repository.find_by_id(self.file_id, self.tenant_id)
        if file_upload is None:
            raise FileNotFoundError(str(self.file_id))
        await self._ensure_case(file_upload)

        temporal_workflow_id = build_job_id(self.workflow_case_id or self.workflow_id, self.file_id)
        logger.info(
            f"dispatcher.start workflow_id={self.workflow_id} file_id={self.file_id} "
            f"case_id={self.workflow_case_id} temporal_workflow_id={temporal_workflow_id} "
            f"force_restart={self.force_restart}"
        )
        processing_job = await self._upsert_processing_job(temporal_workflow_id)
        logger.info(
            f"dispatcher.processing_job processing_job_uuid={processing_job.uuid} "
            f"status={processing_job.status} is_idempotent_skip={processing_job.status.is_idempotent_skip}"
        )

        if not self.force_restart and processing_job.status.is_idempotent_skip:
            logger.warning(
                f"dispatcher.idempotent_skip temporal_workflow_id={temporal_workflow_id} "
                f"status={processing_job.status} — Temporal workflow NOT re-dispatched"
            )
            return processing_job

        doctypes = await DocumentTypeLister(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            document_type_repository=self.document_type_repository,
        ).execute()
        logger.info(
            f"dispatcher.doctypes_loaded workflow_id={self.workflow_id} count={len(doctypes)} "
            f"uuids={[str(dt.uuid) for dt in doctypes]} names={[dt.name for dt in doctypes]}"
        )
        if not doctypes:
            logger.warning(
                f"dispatcher.no_doctypes workflow_id={self.workflow_id} — "
                f"classify_pages will receive an empty document_types list and produce 0 WorkflowDocuments"
            )

        # E4 · diseño §3: si la receta sellada contiene await_documents, el run
        # de upload corre SOLO las fases document-scope; las case-scope viven en
        # el run CASE#. Sin await_documents todo sigue como hoy (full run).
        scope = await self._resolve_scope(resolved)

        # Commit BEFORE starting Temporal so the worker can see the row when
        # its first activity (`update_workflow_processing_job_status`) runs.
        await self.session.commit()

        if self.force_restart:
            await self._terminate_existing(temporal_workflow_id)

        try:
            logger.info(
                f"dispatcher.start_workflow temporal_workflow_id={temporal_workflow_id} "
                f"object_key={file_upload.s3_key} doctypes_count={len(doctypes)} persist=True "
                f"pipeline_id={resolved.pipeline_id} version={resolved.version}"
            )
            await self.temporal_client.start_workflow(
                PipelineInterpreterWorkflow.run,
                PipelineRunInput(
                    pipeline_id=resolved.pipeline_id,
                    version=resolved.version,
                    scope=scope,
                    document=DocumentProcessingInput(
                        object_key=file_upload.s3_key,
                        document_types=[doctype_to_temporal_dict(dt) for dt in doctypes],
                        job_id=temporal_workflow_id,
                        case_id=self.workflow_case_id,
                        workflow_id=self.workflow_id,
                        tenant_id=self.tenant_id,
                        file_id=self.file_id,
                        file_name=file_upload.file_name,
                        processing_job_uuid=processing_job.uuid,
                        persist=True,
                    ),
                ),
                id=temporal_workflow_id,
                task_queue=self.task_queue,
            )
            logger.info(f"dispatcher.workflow_started temporal_workflow_id={temporal_workflow_id}")
        except WorkflowAlreadyStartedError:
            logger.warning(
                f"dispatcher.workflow_already_started temporal_workflow_id={temporal_workflow_id} — "
                f"Temporal already has this workflow id; new dispatch was a no-op"
            )

        return processing_job

    async def _resolve_scope(self, resolved) -> str | None:
        from src.common.domain.enums.pipelines import PhaseKind

        version = await self.pipeline_repository.get_version(resolved.pipeline_id, resolved.version)
        if version is not None and any(
            phase.kind == PhaseKind.AWAIT_DOCUMENTS for phase in version.phases
        ):
            return "document"
        return None

    async def _resolve_pipeline(self, workflow: Workflow):
        # ADR 0002: el workflow corre SIEMPRE su pipeline propio. El override por
        # slug (catálogo tenant compartido) desapareció — ``pipeline_slug`` queda
        # como parámetro M2M deprecado y se ignora.
        return await resolve_workflow_pipeline(
            tenant_id=self.tenant_id,
            pipeline_repository=self.pipeline_repository,
            workflow_id=self.workflow_id,
        )

    async def _load_workflow(self) -> Workflow:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))
        return workflow

    async def _ensure_case(self, file_upload) -> None:
        """Caso universal (E7 · F1): garantiza que ``self.workflow_case_id`` apunta
        a un caso del workflow. El guard de tipo↔caso (STANDARD sin caso / ANALYSIS
        con caso) ya no aplica — todo upload tiene caso.

        - Con ``workflow_case_id`` explícito (ANALYSIS / re-extracción): valida la
          pertenencia al workflow (CaseNotFoundError si no encaja).
        - Sin él (uploads STANDARD): find-or-create de un caso ``per_upload``
          idempotente por archivo (``external_ref="upload:<file_id>"``); nombre =
          nombre de archivo + sufijo corto (decisión Vic 2026-06-11).
        """
        if self.workflow_case_id is not None:
            case = await self.workflow_case_repository.find_by_id(self.workflow_case_id, self.tenant_id)
            if case is None or case.workflow_id != self.workflow_id:
                raise CaseNotFoundError(str(self.workflow_case_id))
            return

        short = self.file_id.hex[:4]
        name = f"{file_upload.file_name} · {short}" if file_upload.file_name else f"Upload {short}"
        result = await FindOrCreateCaseM2M(
            tenant_id=self.tenant_id,
            workflow_id=self.workflow_id,
            workflow_repository=self.workflow_repository,
            case_repository=self.workflow_case_repository,
            pipeline_repository=self.pipeline_repository,
            external_ref=f"upload:{self.file_id.hex}",
            name=name,
        ).execute()
        self.workflow_case_id = result.case.uuid

    async def _upsert_processing_job(self, temporal_workflow_id: str) -> WorkflowProcessingJob:
        existing = await self.processing_job_repository.find_by_temporal_workflow_id(temporal_workflow_id)

        if existing is None:
            return await self.processing_job_repository.create(
                WorkflowProcessingJob(
                    uuid=uuid4(),
                    temporal_workflow_id=temporal_workflow_id,
                    tenant_id=self.tenant_id,
                    workflow_id=self.workflow_id,
                    workflow_case_id=self.workflow_case_id,
                    file_id=self.file_id,
                    created_by_id=self.created_by_id,
                    trigger=self.trigger,
                )
            )

        if self.force_restart or existing.status.is_failed:
            await self.processing_job_repository.reset_to_pending(existing.uuid, trigger=self.trigger)
            # Keep the returned entity consistent with the DB row we just
            # updated; the response presenter would otherwise render the
            # stale terminal state.
            existing.status = WorkflowProcessingJobStatus.PENDING
            existing.error = None
            existing.started_at = None
            existing.finished_at = None
            existing.trigger = self.trigger
        return existing

    async def _terminate_existing(self, temporal_workflow_id: str) -> None:
        try:
            handle = self.temporal_client.get_workflow_handle(temporal_workflow_id)
            await handle.terminate(reason="re-extract requested")
        except Exception:  # noqa: BLE001
            # Workflow may not exist or be already closed — that's fine.
            pass
