"""Activities de las fases case-scope del intérprete (E2 · analyze/output/deliver).

- ``create_analysis_run``: crea la fila del run ANTES del child workflow
  (patrón del starter manual), idempotente por ``run_id`` determinista; si hay
  un run activo AJENO lanza error REINTENTABLE — el retry policy de la fase es
  la espera, así los uploads concurrentes al mismo caso se serializan.
- ``mark_analysis_run_failed``: red de seguridad si el child muere sin
  finalizar su fila (el padre no debe dejar runs RUNNING huérfanos).
- ``build_case_output``: ejecuta el spec case-output — outputs por documento +
  proyección x-source + síntesis LLM acotada (SynthesisRunner extendido).
- ``dispatch_case_event``: emite ``case.output.ready`` / ``case.failed`` al
  outbox → ``workflow_destinations`` (clon del patrón summary_dispatcher;
  idempotencia aplicativa por (type, case:run, destination)).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity
from temporalio.exceptions import ApplicationError

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.analysis_run_processing import (
    BuildCaseOutputInput,
    BuildCaseOutputOutput,
    CreateAnalysisRunForPipelineInput,
    CreateAnalysisRunForPipelineOutput,
    DispatchCaseEventInput,
    MarkAnalysisRunFailedInput,
)
from src.common.domain.enums.run_summary import NarrativeStatus
from src.common.domain.enums.workflow_rules import (
    WorkflowAnalysisRunStatus,
    WorkflowAnalysisRunTrigger,
)
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun

logger = get_logger(__name__)

ACTIVE_RUN_WAIT_ERROR = "analysis.active_run_wait"


class CaseAnalysisRunActivities:
    """Creación/safety-net de runs de análisis nacidos de la fase analyze."""

    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    @activity.defn(name="create_analysis_run")
    async def create_analysis_run(
        self, payload: CreateAnalysisRunForPipelineInput
    ) -> CreateAnalysisRunForPipelineOutput:
        from src.workflows.infrastructure.repositories.sql_workflow_analysis_run import (
            SQLWorkflowAnalysisRunRepository,
        )

        data = CreateAnalysisRunForPipelineInput.model_validate(payload)
        async with self._session_maker() as session:
            repo = SQLWorkflowAnalysisRunRepository(session)

            # Idempotencia: el run_id es determinista (workflow.uuid4 del
            # intérprete) — un retry de la activity encuentra su propia fila.
            existing = await repo.find_by_id(data.run_id, data.tenant_id)
            if existing is not None:
                return CreateAnalysisRunForPipelineOutput(run_id=data.run_id, created=False)

            active = await repo.find_active_for_case(data.case_id, data.tenant_id)
            if active is not None:
                # Run activo AJENO: esperar (retryable). El run que arranque
                # después snapshotea TODOS los docs EXTRACTED del caso, así
                # que serializar pierde nada y cubre los uploads concurrentes.
                raise ApplicationError(
                    f"active analysis run {active.uuid} for case {data.case_id} — waiting",
                    type=ACTIVE_RUN_WAIT_ERROR,
                    non_retryable=False,
                )

            run = WorkflowAnalysisRun(
                uuid=data.run_id,
                tenant_id=data.tenant_id,
                workflow_id=data.workflow_id,
                workflow_case_id=data.case_id,
                status=WorkflowAnalysisRunStatus.RUNNING,
                trigger=WorkflowAnalysisRunTrigger.SYSTEM,
                triggered_by=None,
                started_at=datetime.now(UTC),
            )
            await repo.create(run)
            logger.info(
                "case_phase.analysis_run_created",
                run_id=str(data.run_id),
                case_id=str(data.case_id),
            )
            return CreateAnalysisRunForPipelineOutput(run_id=data.run_id, created=True)

    @activity.defn(name="mark_analysis_run_failed")
    async def mark_analysis_run_failed(self, payload: MarkAnalysisRunFailedInput) -> None:
        from src.workflows.infrastructure.repositories.sql_workflow_analysis_run import (
            SQLWorkflowAnalysisRunRepository,
        )

        data = MarkAnalysisRunFailedInput.model_validate(payload)
        async with self._session_maker() as session:
            repo = SQLWorkflowAnalysisRunRepository(session)
            run = await repo.find_by_id(data.run_id, data.tenant_id)
            if run is None or run.status not in (
                WorkflowAnalysisRunStatus.RUNNING,
                WorkflowAnalysisRunStatus.CANCELING,
            ):
                return
            await repo.update_status(
                run_id=data.run_id,
                tenant_id=data.tenant_id,
                status=WorkflowAnalysisRunStatus.FAILED,
                error=data.error,
                completed=True,
            )


class BuildCaseOutputActivity:
    """Fase output: outputs por documento + proyección x-source + síntesis."""

    def __init__(self, session_maker: async_sessionmaker, synthesizer_agent) -> None:
        self._session_maker = session_maker
        self._agent = synthesizer_agent

    @activity.defn(name="build_case_output")
    async def build_case_output(self, payload: BuildCaseOutputInput) -> BuildCaseOutputOutput:
        from src.tenants.infrastructure.repositories.sql_tenant import SQLTenantRepository
        from src.workflows.application.analysis_run_summary.document_output import (
            BuildDocumentOutputs,
        )
        from src.workflows.application.analysis_run_summary.synthesis_runner import SynthesisRunner
        from src.workflows.domain.run_summary.errors import SynthesisDisabledError
        from src.workflows.infrastructure.repositories.sql_document_repository import (
            SQLWorkflowDocumentRepository,
        )
        from src.workflows.infrastructure.repositories.sql_document_type import (
            SQLDocumentTypeRepository,
        )
        from src.workflows.infrastructure.repositories.sql_run_summary import (
            SQLWorkflowAnalysisRunSummaryRepository,
        )
        from src.workflows.infrastructure.repositories.sql_workflow import SQLWorkflowRepository
        from src.workflows.infrastructure.repositories.sql_workflow_analysis_run import (
            SQLWorkflowAnalysisRunRepository,
        )
        from src.workflows.infrastructure.repositories.sql_workflow_rule import (
            SQLWorkflowRuleRepository,
        )
        from src.workflows.infrastructure.repositories.sql_workflow_rule_result import (
            SQLWorkflowRuleResultRepository,
        )

        from src.workflows.infrastructure.services.rules.bootstrap import build_synthesizer_agent

        data = BuildCaseOutputInput.model_validate(payload)
        # phases-config: provider override per-pipeline ⇒ synthesizer per-call;
        # sin override usa el singleton del worker (env-default, comportamiento de hoy).
        synthesizer = (
            build_synthesizer_agent(data.synthesizer_provider)
            if data.synthesizer_provider
            else self._agent
        )
        warnings: list[str] = []
        async with self._session_maker() as session:
            tenant = await SQLTenantRepository(session=session).find(data.tenant_id)

            doc_outputs = await BuildDocumentOutputs(
                run_id=data.run_id,
                case_id=data.case_id,
                workflow_id=data.workflow_id,
                tenant_id=data.tenant_id,
                document_repository=SQLWorkflowDocumentRepository(session=session),
                document_type_repository=SQLDocumentTypeRepository(session=session),
                rule_repository=SQLWorkflowRuleRepository(session=session),
                result_repository=SQLWorkflowRuleResultRepository(session=session),
            ).execute()

            summary = None
            try:
                summary = await SynthesisRunner(
                    run_id=data.run_id,
                    tenant_id=data.tenant_id,
                    workflow_repository=SQLWorkflowRepository(session=session),
                    run_repository=SQLWorkflowAnalysisRunRepository(session=session),
                    result_repository=SQLWorkflowRuleResultRepository(session=session),
                    summary_repository=SQLWorkflowAnalysisRunSummaryRepository(session=session),
                    agent=synthesizer,
                    tenant=tenant,
                    document_repository=SQLWorkflowDocumentRepository(session=session),
                    # Sin estos dos, los x-source @slug/@rule degradan a null:
                    document_type_repository=SQLDocumentTypeRepository(session=session),
                    rule_repository=SQLWorkflowRuleRepository(session=session),
                ).execute()
            except SynthesisDisabledError:
                # Sin síntesis NI x-source: el caso entrega solo verdict — el
                # summary determinista ya lo creó el child (complete_run).
                warnings.append("synthesis_disabled_no_projection")
                summary = await SQLWorkflowAnalysisRunSummaryRepository(session=session).find_by_run(
                    data.run_id, data.tenant_id
                )

            if summary is None:
                raise ApplicationError(
                    f"no summary for analysis run {data.run_id}",
                    type="pipeline.output_no_summary",
                    non_retryable=True,
                )
            narrative = summary.narrative_status
            if narrative == NarrativeStatus.FAILED:
                raise ApplicationError(
                    f"synthesis failed for run {data.run_id}: {summary.narrative_error}",
                    type="pipeline.output_synthesis_failed",
                    non_retryable=True,
                )

            return BuildCaseOutputOutput(
                run_id=data.run_id,
                verdict=summary.verdict.value if summary.verdict else None,
                narrative_status=narrative.value if narrative else None,
                has_output=summary.output is not None,
                document_outputs=len(doc_outputs),
                warnings=warnings[:20],
            )


class DispatchCaseEventActivity:
    """Fase deliver: encola+entrega eventos case.* (outbox + HMAC, patrón W1).

    La lógica vive en :class:`CaseEventDispatcher` (E3) para que los endpoints
    M2M (``case.created``) la reutilicen fuera de Temporal.
    """

    def __init__(self, session_maker: async_sessionmaker, dispatcher=None) -> None:
        from src.workflows.infrastructure.services.webhooks.case_event_dispatcher import (
            CaseEventDispatcher,
        )

        self._service = CaseEventDispatcher(session_maker=session_maker, dispatcher=dispatcher)

    @activity.defn(name="dispatch_case_event")
    async def dispatch_case_event(self, payload: DispatchCaseEventInput) -> int:
        return await self._service.dispatch(DispatchCaseEventInput.model_validate(payload))
