"""Activities del fan-out a child cases (E5 · diseño §2).

- ``create_child_cases``: idempotente (clave determinista
  ``(parent_case_id, document_index)`` materializada como ``external_ref``,
  check-then-insert) — crea los children con lineage/herencia sellada,
  reasigna los docs clasificados (``source=SPLIT_CHILD``) y emite el webhook
  ``case.created`` por cada child REALMENTE creado (con ``parentCaseId``,
  best-effort). Devuelve refs compactos (límite 2 MiB de Temporal).
- ``start_child_case_runs``: batch (≤20) desde ``finalize`` — por child,
  ``EnsureCaseRunStarted`` (CASE# propio, idempotente) + señal
  ``case_docs_changed`` best-effort (patrón ``signal_case_workflow``).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity
from temporalio.client import Client as TemporalClient

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.analysis_run_processing import (
    DispatchCaseEventInput,
)
from src.common.domain.entities.workflows.case_runtime import (
    ChildCaseRef,
    CreateChildCasesInput,
    CreateChildCasesOutput,
    StartChildCaseRunsInput,
    StartChildCaseRunsOutput,
)
from src.common.domain.enums.webhooks import WebhookEventType

logger = get_logger(__name__)

CREATE_CHILD_CASES_ACTIVITY = "create_child_cases"
START_CHILD_CASE_RUNS_ACTIVITY = "start_child_case_runs"


class CreateChildCasesActivity:
    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    @activity.defn(name=CREATE_CHILD_CASES_ACTIVITY)
    async def create_child_cases(self, payload: CreateChildCasesInput) -> CreateChildCasesOutput:
        from src.workflows.application.workflow_cases.fan_out import CreateChildCases
        from src.workflows.infrastructure.repositories.sql_document_repository import (
            SQLWorkflowDocumentRepository,
        )
        from src.workflows.infrastructure.repositories.sql_workflow_case import (
            SQLWorkflowCaseRepository,
        )

        data = CreateChildCasesInput.model_validate(payload)
        async with self._session_maker() as session:
            result = await CreateChildCases(
                tenant_id=data.tenant_id,
                workflow_id=data.workflow_id,
                parent_case_id=data.parent_case_id,
                documents=data.documents,
                case_repository=SQLWorkflowCaseRepository(session),
                document_repository=SQLWorkflowDocumentRepository(session=session),
                # C2: namespacea la clave del child por origen del run.
                file_id=data.file_id,
                processing_job_uuid=data.processing_job_uuid,
            ).execute()

        # Webhook ``case.created`` por cada child REALMENTE creado (idempotencia:
        # los retries encuentran los children existentes y no re-emiten).
        # Best-effort fuera de la sesión: los children ya están commiteados.
        for child in result.children:
            if not child.created:
                continue
            await self._dispatch_child_created(data, child.case)

        logger.info(
            "fan_out.children_ensured",
            parent_case_id=str(data.parent_case_id),
            total=len(result.children),
            created=result.created_count,
        )
        return CreateChildCasesOutput(
            children=[
                ChildCaseRef(
                    case_id=child.case.uuid,
                    document_index=child.document_index,
                    external_ref=child.case.external_ref,
                )
                for child in result.children
            ],
            created=result.created_count,
        )

    async def _dispatch_child_created(self, data: CreateChildCasesInput, case) -> None:
        from src.workflows.infrastructure.services.webhooks.case_event_dispatcher import (
            CaseEventDispatcher,
        )

        try:
            await CaseEventDispatcher(session_maker=self._session_maker).dispatch(
                DispatchCaseEventInput(
                    tenant_id=data.tenant_id,
                    workflow_id=data.workflow_id,
                    case_id=case.uuid,
                    event_type=WebhookEventType.CASE_CREATED.value,
                    # `error` es la bolsa de metadatos de case.created (gotcha E3).
                    error={
                        "externalRef": case.external_ref,
                        "name": case.name,
                        "parentCaseId": str(data.parent_case_id),
                    },
                )
            )
        except Exception:  # noqa: BLE001 — el webhook jamás rompe el fan-out
            logger.exception("fan_out.child_created_dispatch_failed", case_id=str(case.uuid))


class StartChildCaseRunsActivity:
    """Arranque + señal de los CASE# de los children (batch desde finalize)."""

    def __init__(
        self,
        session_maker: async_sessionmaker,
        temporal_client: TemporalClient,
        task_queue: str,
    ) -> None:
        self._session_maker = session_maker
        self._client = temporal_client
        self._task_queue = task_queue

    @activity.defn(name=START_CHILD_CASE_RUNS_ACTIVITY)
    async def start_child_case_runs(
        self, payload: StartChildCaseRunsInput
    ) -> StartChildCaseRunsOutput:
        from src.workflows.application.workflow_cases.case_run_starter import (
            CASE_DOCS_CHANGED_SIGNAL,
            EnsureCaseRunStarted,
            signal_case_run,
        )
        from src.workflows.infrastructure.repositories.sql_pipeline import SQLPipelineRepository
        from src.workflows.infrastructure.repositories.sql_workflow import SQLWorkflowRepository
        from src.workflows.infrastructure.repositories.sql_workflow_case import (
            SQLWorkflowCaseRepository,
        )

        data = StartChildCaseRunsInput.model_validate(payload)
        started = 0
        signaled = 0
        for case_id in data.case_ids:
            # Sesión por child: un fallo no envenena el resto del batch.
            try:
                async with self._session_maker() as session:
                    result = await EnsureCaseRunStarted(
                        tenant_id=data.tenant_id,
                        case_id=case_id,
                        case_repository=SQLWorkflowCaseRepository(session),
                        pipeline_repository=SQLPipelineRepository(session=session),
                        workflow_repository=SQLWorkflowRepository(session=session),
                        temporal_client=self._client,
                        task_queue=self._task_queue,
                    ).execute()
                if result.started:
                    started += 1
            except Exception:  # noqa: BLE001 — best-effort por child (patrón señal E4)
                logger.exception("fan_out.child_run_start_failed", case_id=str(case_id))
                continue
            if await signal_case_run(self._client, case_id, CASE_DOCS_CHANGED_SIGNAL):
                signaled += 1
        return StartChildCaseRunsOutput(started=started, signaled=signaled)
