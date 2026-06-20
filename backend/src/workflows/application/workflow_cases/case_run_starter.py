"""Arranque (idempotente) del run de caso ``CASE#`` (E4 · diseño §3).

Si la receta sellada/efectiva del caso contiene ``await_documents``, el caso
tiene un run propio ``PipelineInterpreterWorkflow`` con id
``CASE#{case_uuid.hex}`` y ``scope="case"`` que espera completitud y corre las
fases case-scope. Se invoca al crear el caso (POST /v1/cases, UI, ingest) y
desde POST /v1/cases/{id}/ready — ``WorkflowAlreadyStarted`` se ignora.
Sella ``workflow_cases.pipeline_version_id`` al arrancar si era NULL.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from temporalio.client import Client as TemporalClient
from temporalio.exceptions import WorkflowAlreadyStartedError

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.document_processing import DocumentProcessingInput
from src.common.domain.entities.workflows.pipeline_run import PipelineRunInput
from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.workflows.application.workflow_cases.recipe_resolver import (
    recipe_has_await_documents,
    resolve_case_recipe,
)
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository

logger = get_logger(__name__)

CASE_RUN_PREFIX = "CASE#"

# Señales del CASE# workflow (pipeline_interpreter.py, patrón task_resolved).
CASE_DOCS_CHANGED_SIGNAL = "case_docs_changed"
CASE_READY_SIGNAL = "case_ready"
# E5 · fan-out: el run document-scope partió el caso en children — el CASE#
# del padre sale de await_documents y salta las fases case-scope restantes.
CASE_SPLIT_SIGNAL = "case_split"


def case_run_workflow_id(case_id: UUID) -> str:
    return f"{CASE_RUN_PREFIX}{case_id.hex}"


async def signal_case_run(
    temporal_client: TemporalClient,
    case_id: UUID,
    signal: str,
    payload: dict | None = None,
) -> bool:
    """Señal best-effort al CASE# (si no corre, no pasa nada — jamás levanta)."""
    try:
        handle = temporal_client.get_workflow_handle(case_run_workflow_id(case_id))
        if payload is None:
            await handle.signal(signal)
        else:
            await handle.signal(signal, payload)
        return True
    except Exception:
        logger.warning("case_run.signal_failed", case_id=str(case_id), signal=signal)
        return False


@dataclass
class EnsureCaseRunStartedResult:
    started: bool
    has_await_documents: bool
    run_id: str | None = None


@dataclass
class EnsureCaseRunStarted(UseCase):
    tenant_id: UUID
    case_id: UUID
    case_repository: WorkflowCaseRepository
    pipeline_repository: PipelineRepository
    temporal_client: TemporalClient
    task_queue: str
    workflow_repository: WorkflowRepository | None = None

    async def execute(self) -> EnsureCaseRunStartedResult:
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if case is None:
            raise CaseNotFoundError(str(self.case_id))

        version = await resolve_case_recipe(
            case,
            self.tenant_id,
            pipeline_repository=self.pipeline_repository,
            workflow_repository=self.workflow_repository,
        )
        if not recipe_has_await_documents(version):
            return EnsureCaseRunStartedResult(started=False, has_await_documents=False)

        # Sella la versión al arrancar (si era NULL) — el CASE# y la API de
        # completeness leen SIEMPRE la misma receta a partir de aquí.
        if case.pipeline_version_id is None:
            case.pipeline_version_id = version.uuid
            await self.case_repository.update(case)

        run_id = case_run_workflow_id(case.uuid)
        from src.workflows.presentation.workflows.pipeline_interpreter import (
            PipelineInterpreterWorkflow,
        )

        try:
            await self.temporal_client.start_workflow(
                PipelineInterpreterWorkflow.run,
                PipelineRunInput(
                    pipeline_id=version.pipeline_id,
                    version=version.version,
                    scope="case",
                    document=DocumentProcessingInput(
                        object_key="",
                        document_types=[],
                        job_id=run_id,
                        case_id=case.uuid,
                        workflow_id=case.workflow_id,
                        tenant_id=self.tenant_id,
                        persist=True,
                    ),
                ),
                id=run_id,
                task_queue=self.task_queue,
            )
            logger.info("case_run.started", case_id=str(case.uuid), run_id=run_id)
            started = True
        except WorkflowAlreadyStartedError:
            started = False
        return EnsureCaseRunStartedResult(started=started, has_await_documents=True, run_id=run_id)
