"""Activities del motor de caso E4 (await_documents · extraction_gate · review).

- ``evaluate_case_completeness``: cuenta docs EXTRACTED (incluye virtuales) vs
  ``await_documents.config.required_types`` (completitud plegada, D-A); persiste snapshot en
  ``workflow_cases.completeness`` y appendea ``completeness.evaluated`` SOLO
  si cambió.
- ``mark_case_ready``: ``ready_at=now`` si NULL, transición RECEIVING→PROCESSING
  (vía el choke point) y case_event ``ready`` {forced, auto}.
- ``append_case_event``: timeline append-only genérico para las fases.
- ``evaluate_activation_gate``: confianza fusionada capa-2→capa-1 vs umbrales
  de la ActivationPolicy; etiqueta ``needs_clarification`` (paridad legacy) y
  devuelve los breach items camelCase.
- ``open_clarification_task`` / ``open_approval_task``: HumanTask idempotente
  por task_key con payload rico (clarification request §4.5 / contexto de
  aprobación del último run).
- ``check_blocking_results``: ¿el último run COMPLETED tiene señales FAIL con
  severidad bloqueante? (modo by_exception).
- ``signal_case_workflow``: señal best-effort al CASE# (la usa finalize de los
  runs document-scope y cualquier productor de documentos).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity
from temporalio.client import Client as TemporalClient

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.case_runtime import (
    AppendCaseEventInput,
    BuildStageGateItemsInput,
    BuildStageGateItemsOutput,
    CheckBlockingResultsInput,
    CheckBlockingResultsOutput,
    EvaluateActivationGateInput,
    EvaluateActivationGateOutput,
    EvaluateCaseCompletenessInput,
    EvaluateCaseCompletenessOutput,
    MarkCaseReadyInput,
    MarkCaseReadyOutput,
    OpenApprovalTaskInput,
    OpenCaseTaskOutput,
    OpenClarificationTaskInput,
    OpenQaAuditTaskInput,
    OpenQaAuditTaskOutput,
    ResolveClassifierInput,
    ResolveClassifierOutput,
    SignalCaseWorkflowInput,
)
from src.common.domain.enums.human_tasks import HumanTaskAssigneeMode, HumanTaskKind
from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
from src.common.domain.enums.workflow_rules import WorkflowAnalysisRunStatus

logger = get_logger(__name__)

EVALUATE_CASE_COMPLETENESS_ACTIVITY = "evaluate_case_completeness"
MARK_CASE_READY_ACTIVITY = "mark_case_ready"
APPEND_CASE_EVENT_ACTIVITY = "append_case_event"
EVALUATE_ACTIVATION_GATE_ACTIVITY = "evaluate_activation_gate"
OPEN_CLARIFICATION_TASK_ACTIVITY = "open_clarification_task"
OPEN_APPROVAL_TASK_ACTIVITY = "open_approval_task"
CHECK_BLOCKING_RESULTS_ACTIVITY = "check_blocking_results"
BUILD_STAGE_GATE_ITEMS_ACTIVITY = "build_stage_gate_items"
SIGNAL_CASE_WORKFLOW_ACTIVITY = "signal_case_workflow"
OPEN_QA_AUDIT_TASK_ACTIVITY = "open_qa_audit_task"
RESOLVE_CLASSIFIER_ACTIVITY = "resolve_classifier"

READY_EVENT = "ready"
# E6 · §3: QA sampling post-COMPLETED. "Auto-aprobado" = el gate de revisión
# se SALTÓ (review.skipped) y NINGÚN humano aprobó (review.approved). qa.sampled
# marca el caso elegido para auditoría.
REVIEW_SKIPPED_EVENT = "review.skipped"
REVIEW_APPROVED_EVENT = "review.approved"
QA_SAMPLED_EVENT = "qa.sampled"


class CaseRuntimeActivities:
    """Activities con acceso a BD para las fases case-scope (E4)."""

    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    # ── resolve_classifier (F3 · D-C) ─────────────────────────────────────

    @activity.defn(name=RESOLVE_CLASSIFIER_ACTIVITY)
    async def resolve_classifier(self, payload: ResolveClassifierInput) -> ResolveClassifierOutput:
        from src.workflows.domain.services.classifier_resolver import resolve_classifier_contract
        from src.workflows.infrastructure.repositories.sql_classifier import SQLClassifierRepository

        data = ResolveClassifierInput.model_validate(payload)
        async with self._session_maker() as session:
            classifier = await SQLClassifierRepository(session).find_by_slug(data.slug, data.tenant_id)
        if classifier is None or not classifier.enabled:
            # Degradación segura: classify_pages cae al lambda base.
            return ResolveClassifierOutput(found=False)
        contract = resolve_classifier_contract(classifier)
        return ResolveClassifierOutput(
            found=True,
            kind=contract["kind"],
            lambda_function=contract.get("lambda_function"),
            lambda_alias=contract.get("lambda_alias"),
            config=contract.get("config") or {},
        )

    # ── await_documents ──────────────────────────────────────────────────

    @activity.defn(name=EVALUATE_CASE_COMPLETENESS_ACTIVITY)
    async def evaluate_case_completeness(
        self, payload: EvaluateCaseCompletenessInput
    ) -> EvaluateCaseCompletenessOutput:
        from src.workflows.application.workflow_cases.completeness import (
            EvaluateCaseCompleteness,
        )
        from src.workflows.infrastructure.repositories.sql_case_event import (
            SQLCaseEventRepository,
        )
        from src.workflows.infrastructure.repositories.sql_document_repository import (
            SQLWorkflowDocumentRepository,
        )
        from src.workflows.infrastructure.repositories.sql_document_type import (
            SQLDocumentTypeRepository,
        )
        from src.workflows.infrastructure.repositories.sql_pipeline import SQLPipelineRepository
        from src.workflows.infrastructure.repositories.sql_workflow import SQLWorkflowRepository
        from src.workflows.infrastructure.repositories.sql_workflow_case import (
            SQLWorkflowCaseRepository,
        )

        data = EvaluateCaseCompletenessInput.model_validate(payload)
        async with self._session_maker() as session:
            result = await EvaluateCaseCompleteness(
                tenant_id=data.tenant_id,
                case_id=data.case_id,
                case_repository=SQLWorkflowCaseRepository(session),
                document_repository=SQLWorkflowDocumentRepository(session=session),
                document_type_repository=SQLDocumentTypeRepository(session=session),
                pipeline_repository=SQLPipelineRepository(session=session),
                workflow_repository=SQLWorkflowRepository(session=session),
                case_event_repository=SQLCaseEventRepository(session),
                persist=True,
            ).execute()
        return EvaluateCaseCompletenessOutput(
            satisfied=result.satisfied,
            auto_ready=result.auto_ready,
            required=result.snapshot.get("required") or {},
            present=result.snapshot.get("present") or {},
            missing=result.snapshot.get("missing") or [],
            changed=result.changed,
            # E5 · fan-out: un child nace completo — await_documents lo
            # auto-readea al primer case_docs_changed.
            is_child=result.case.parent_case_id is not None,
        )

    @activity.defn(name=MARK_CASE_READY_ACTIVITY)
    async def mark_case_ready(self, payload: MarkCaseReadyInput) -> MarkCaseReadyOutput:
        from src.workflows.application.workflow_cases.transition import TransitionCaseStatus
        from src.workflows.domain.models.case_event import CaseEvent
        from src.workflows.domain.services.case_state_machine import can_transition
        from src.workflows.infrastructure.repositories.sql_case_event import (
            SQLCaseEventRepository,
        )
        from src.workflows.infrastructure.repositories.sql_workflow_case import (
            SQLWorkflowCaseRepository,
        )

        data = MarkCaseReadyInput.model_validate(payload)
        async with self._session_maker() as session:
            case_repo = SQLWorkflowCaseRepository(session)
            event_repo = SQLCaseEventRepository(session)
            case = await case_repo.find_by_id(data.case_id, data.tenant_id)
            if case is None:
                return MarkCaseReadyOutput(ready_at=None, transitioned=False)

            newly_ready = case.ready_at is None
            if newly_ready:
                case.ready_at = datetime.now(UTC)
                case = await case_repo.update(case)

            transitioned = False
            if case.status != WorkflowCaseStatus.PROCESSING and can_transition(
                case.status, WorkflowCaseStatus.PROCESSING
            ):
                result = await TransitionCaseStatus(
                    tenant_id=data.tenant_id,
                    case_id=data.case_id,
                    to_status=WorkflowCaseStatus.PROCESSING,
                    case_repository=case_repo,
                    case_event_repository=event_repo,
                    reason="case.ready",
                    actor="system",
                ).execute()
                transitioned = result.changed

            if newly_ready:
                await event_repo.create(
                    CaseEvent(
                        uuid=uuid4(),
                        tenant_id=data.tenant_id,
                        case_id=data.case_id,
                        type=READY_EVENT,
                        payload={"forced": data.forced, "auto": data.auto},
                        actor="system",
                    )
                )
        return MarkCaseReadyOutput(
            ready_at=case.ready_at.isoformat() if case.ready_at else None,
            transitioned=transitioned,
        )

    # ── timeline ─────────────────────────────────────────────────────────

    @activity.defn(name=APPEND_CASE_EVENT_ACTIVITY)
    async def append_case_event(self, payload: AppendCaseEventInput) -> None:
        from src.workflows.domain.models.case_event import CaseEvent
        from src.workflows.infrastructure.repositories.sql_case_event import (
            SQLCaseEventRepository,
        )

        data = AppendCaseEventInput.model_validate(payload)
        async with self._session_maker() as session:
            await SQLCaseEventRepository(session).create(
                CaseEvent(
                    uuid=uuid4(),
                    tenant_id=data.tenant_id,
                    case_id=data.case_id,
                    type=data.type,
                    payload=data.payload,
                    actor=data.actor or "system",
                    dedupe_key=data.dedupe_key,
                )
            )

    # ── QA sampling post-COMPLETED (E6 · §3) ──────────────────────────────

    @activity.defn(name=OPEN_QA_AUDIT_TASK_ACTIVITY)
    async def open_qa_audit_task(self, payload: OpenQaAuditTaskInput) -> OpenQaAuditTaskOutput:
        """Abre (idempotente) la HumanTask de auditoría QA si el caso fue
        AUTO-aprobado. No-op si un humano aprobó (review.approved) o si no hubo
        review.skipped. Fire-and-forget: la task no pausa el run (sin
        ``pipeline_run_id``) — el run ya terminó."""
        from src.workflows.domain.models.case_event import CaseEvent
        from src.workflows.domain.models.human_task import HumanTask
        from src.workflows.infrastructure.repositories.sql_case_event import (
            SQLCaseEventRepository,
        )
        from src.workflows.infrastructure.repositories.sql_human_task import (
            SQLHumanTaskRepository,
        )

        data = OpenQaAuditTaskInput.model_validate(payload)
        async with self._session_maker() as session:
            event_repo = SQLCaseEventRepository(session)
            # Universo QA: review.skipped presente Y review.approved ausente.
            events = await event_repo.list_by_case(data.case_id, data.tenant_id, limit=500)
            types = {e.type for e in events}
            auto_approved = REVIEW_SKIPPED_EVENT in types and REVIEW_APPROVED_EVENT not in types
            if not auto_approved:
                return OpenQaAuditTaskOutput(task_id=None, created=False)

            task_id = uuid4()
            qa_payload = {
                "caseId": str(data.case_id),
                "taskId": str(task_id),
                "runId": data.run_id,
                "verdict": None,
            }
            summary = await self._latest_completed_summary(session, data.tenant_id, data.case_id)
            if summary is not None:
                qa_payload["verdict"] = summary.verdict.value if summary.verdict else None
            qa_payload["resolveUrl"] = f"/v1/tasks/{task_id}/resolve"

            task = await SQLHumanTaskRepository(session).upsert(
                HumanTask(
                    uuid=task_id,
                    tenant_id=data.tenant_id,
                    task_key=data.task_key,
                    kind=HumanTaskKind.QA,
                    assignee_mode=HumanTaskAssigneeMode.INTERNAL_QUEUE,
                    audience=data.audience,
                    workflow_id=data.workflow_id,
                    case_id=data.case_id,
                    # Fire-and-forget: jamás un run pausado esperando esta task.
                    pipeline_run_id=None,
                    payload=qa_payload,
                    stage="review_l1",
                )
            )
            await event_repo.create(
                CaseEvent(
                    uuid=uuid4(),
                    tenant_id=data.tenant_id,
                    case_id=data.case_id,
                    type=QA_SAMPLED_EVENT,
                    payload={"taskId": str(task.uuid), "runId": data.run_id},
                    actor="system",
                    dedupe_key=f"{data.task_key}:{QA_SAMPLED_EVENT}",
                )
            )
        return OpenQaAuditTaskOutput(task_id=task.uuid, created=True)

    # ── extraction_gate (activation gate) ────────────────────────────────

    @activity.defn(name=EVALUATE_ACTIVATION_GATE_ACTIVITY)
    async def evaluate_activation_gate(self, payload: EvaluateActivationGateInput) -> EvaluateActivationGateOutput:
        from src.workflows.domain.models.policies import ActivationPolicy
        from src.workflows.domain.services.activation_gate import (
            evaluate_activation_gate,
            flagged_fields_by_document,
        )
        from src.workflows.infrastructure.repositories.sql_document_repository import (
            SQLWorkflowDocumentRepository,
        )
        from src.workflows.infrastructure.repositories.sql_document_type import (
            SQLDocumentTypeRepository,
        )
        from src.workflows.infrastructure.repositories.sql_workflow_case import (
            SQLWorkflowCaseRepository,
        )

        data = EvaluateActivationGateInput.model_validate(payload)
        policy = ActivationPolicy.model_validate(data.activation_policy)
        async with self._session_maker() as session:
            case = await SQLWorkflowCaseRepository(session).find_by_id(data.case_id, data.tenant_id)
            if case is None:
                return EvaluateActivationGateOutput(items=[])
            document_repo = SQLWorkflowDocumentRepository(session=session)
            documents = await document_repo.list_by_case(data.case_id, data.tenant_id)
            doc_types = await SQLDocumentTypeRepository(session=session).list_by_workflow(
                case.workflow_id, data.tenant_id
            )
            slug_by_type_id = {dt.uuid: dt.slug for dt in doc_types if dt.slug}

            items = evaluate_activation_gate(documents, slug_by_type_id, policy)

            # Paridad legacy: etiquetar needs_clarification en los docs con breach.
            flagged = flagged_fields_by_document(items)
            docs_by_id = {str(d.uuid): d for d in documents}
            for document_id, fields in flagged.items():
                doc = docs_by_id.get(document_id)
                if doc is None:
                    continue
                doc.needs_clarification = fields
                await document_repo.update(doc)
        return EvaluateActivationGateOutput(items=items)

    # ── pausas con contexto rico ─────────────────────────────────────────

    @activity.defn(name=OPEN_CLARIFICATION_TASK_ACTIVITY)
    async def open_clarification_task(self, payload: OpenClarificationTaskInput) -> OpenCaseTaskOutput:
        from src.workflows.domain.models.human_task import HumanTask
        from src.workflows.infrastructure.repositories.sql_human_task import (
            SQLHumanTaskRepository,
        )

        data = OpenClarificationTaskInput.model_validate(payload)
        task_id = uuid4()
        expires_at = None
        if data.expires_in_hours and data.expires_in_hours > 0:
            expires_at = datetime.now(UTC) + timedelta(hours=data.expires_in_hours)

        request = {
            "caseId": str(data.case_id),
            "taskId": str(task_id),
            "items": [
                {
                    "fieldPath": item.get("fieldPath"),
                    "reason": "low_confidence",
                    "parseConfidence": item.get("parseConfidence"),
                    "extractConfidence": item.get("extractConfidence"),
                    "signals": item.get("signals") or [],
                    "candidates": (item.get("candidates") or [])[:3],
                    "page": item.get("page"),
                    "bbox": item.get("bbox"),
                    "documentId": item.get("documentId"),
                    "documentType": item.get("documentType"),
                }
                for item in data.items
            ],
            "resolveUrl": f"/v1/tasks/{task_id}/resolve",
            "expiresAt": expires_at.isoformat() if expires_at else None,
        }
        async with self._session_maker() as session:
            task = await SQLHumanTaskRepository(session).upsert(
                HumanTask(
                    uuid=task_id,
                    tenant_id=data.tenant_id,
                    task_key=data.task_key,
                    kind=HumanTaskKind.CLARIFICATION,
                    assignee_mode=HumanTaskAssigneeMode.EXTERNAL_CALLBACK,
                    audience=data.audience,
                    workflow_id=data.workflow_id,
                    case_id=data.case_id,
                    pipeline_run_id=data.pipeline_run_id,
                    payload=request,
                    expires_at=expires_at,
                )
            )
        # Retry/replay: si la task ya existía, su payload (con SU taskId) manda.
        return OpenCaseTaskOutput(task_id=task.uuid, payload=task.payload or request)

    @activity.defn(name=OPEN_APPROVAL_TASK_ACTIVITY)
    async def open_approval_task(self, payload: OpenApprovalTaskInput) -> OpenCaseTaskOutput:
        from src.workflows.domain.models.human_task import HumanTask
        from src.workflows.infrastructure.repositories.sql_human_task import (
            SQLHumanTaskRepository,
        )

        data = OpenApprovalTaskInput.model_validate(payload)
        task_id = uuid4()
        async with self._session_maker() as session:
            task_payload: dict = {"caseId": str(data.case_id), "taskId": str(task_id)}
            # F4 · quórum: el endpoint de resolución lee esto para acumular votos.
            # N=1 (default) ⇒ no se sella nada ⇒ resolución single de hoy (compat).
            if data.approvals_required > 1:
                task_payload["approvalsRequired"] = data.approvals_required
                task_payload["distinctApprovers"] = data.distinct_approvers
                task_payload["approvers"] = {
                    "users": data.approver_users,
                    "roles": data.approver_roles,
                    "audience": data.approver_audience,
                }
            if data.stage:
                task_payload["stage"] = data.stage
            if data.trigger == "gate_review":
                task_payload["items"] = data.gate_items or []
            else:
                # E5 · §3.1: los stages adjuntan sus gate items frescos (el L2
                # ya viene filtrado por verification — patrón Rossum).
                if data.gate_items is not None:
                    task_payload["items"] = data.gate_items
                summary = await self._latest_completed_summary(session, data.tenant_id, data.case_id)
                if summary is not None:
                    task_payload["verdict"] = summary.verdict.value if summary.verdict else None
                    task_payload["summary"] = {
                        "confidenceScore": summary.confidence_score,
                        "signalsByPolarity": summary.signals_by_polarity,
                        "signalsBySeverity": summary.signals_by_severity,
                        "narrativeStatus": (summary.narrative_status.value if summary.narrative_status else None),
                        "hasOutput": summary.output is not None,
                    }
                    task_payload["signals"] = [
                        {
                            "ruleId": str(s.rule_id),
                            "kind": s.kind,
                            "severity": s.severity,
                            "polarity": s.polarity,
                        }
                        for s in (summary.signals or [])[:50]
                    ]
                else:
                    task_payload["verdict"] = None
                    task_payload["summary"] = None
                    task_payload["signals"] = []
            task_payload["resolveUrl"] = f"/v1/tasks/{task_id}/resolve"

            task = await SQLHumanTaskRepository(session).upsert(
                HumanTask(
                    uuid=task_id,
                    tenant_id=data.tenant_id,
                    task_key=data.task_key,
                    kind=HumanTaskKind.APPROVAL,
                    assignee_mode=HumanTaskAssigneeMode.INTERNAL_QUEUE,
                    audience=data.audience,
                    workflow_id=data.workflow_id,
                    case_id=data.case_id,
                    pipeline_run_id=data.pipeline_run_id,
                    payload=task_payload,
                    stage=data.stage,
                )
            )
        return OpenCaseTaskOutput(task_id=task.uuid, payload=task.payload or task_payload)

    # ── human_review multinivel (E5 · §3.1) ──────────────────────────────

    @activity.defn(name=BUILD_STAGE_GATE_ITEMS_ACTIVITY)
    async def build_stage_gate_items(self, payload: BuildStageGateItemsInput) -> BuildStageGateItemsOutput:
        """Gate items frescos del stage: relee los docs del caso AHORA (no el
        snapshot del confidence_gate) y, para L2, excluye los fieldPaths con
        ``verification.level >= exclude_verified_level`` (filtro Rossum).
        Read-only: NO re-etiqueta ``needs_clarification``."""
        from src.workflows.domain.models.policies import ActivationPolicy
        from src.workflows.domain.services.activation_gate import (
            evaluate_activation_gate,
            exclude_verified_items,
        )
        from src.workflows.infrastructure.repositories.sql_document_repository import (
            SQLWorkflowDocumentRepository,
        )
        from src.workflows.infrastructure.repositories.sql_document_type import (
            SQLDocumentTypeRepository,
        )
        from src.workflows.infrastructure.repositories.sql_workflow_case import (
            SQLWorkflowCaseRepository,
        )

        data = BuildStageGateItemsInput.model_validate(payload)
        policy = ActivationPolicy.model_validate(data.activation_policy)
        async with self._session_maker() as session:
            case = await SQLWorkflowCaseRepository(session).find_by_id(data.case_id, data.tenant_id)
            if case is None:
                return BuildStageGateItemsOutput(items=[])
            documents = await SQLWorkflowDocumentRepository(session=session).list_by_case(data.case_id, data.tenant_id)
            doc_types = await SQLDocumentTypeRepository(session=session).list_by_workflow(
                case.workflow_id, data.tenant_id
            )
            slug_by_type_id = {dt.uuid: dt.slug for dt in doc_types if dt.slug}

            items = evaluate_activation_gate(documents, slug_by_type_id, policy)
            if data.exclude_verified_level is not None:
                verification_by_document = {str(doc.uuid): doc.verification or {} for doc in documents}
                items = exclude_verified_items(items, verification_by_document, data.exclude_verified_level)
        return BuildStageGateItemsOutput(items=items)

    # ── human_review by_exception ────────────────────────────────────────

    @activity.defn(name=CHECK_BLOCKING_RESULTS_ACTIVITY)
    async def check_blocking_results(self, payload: CheckBlockingResultsInput) -> CheckBlockingResultsOutput:
        from src.common.domain.enums.workflow_rules import WorkflowRuleVerdictPolarity

        data = CheckBlockingResultsInput.model_validate(payload)
        severities = {s.upper() for s in data.severities}
        async with self._session_maker() as session:
            summary = await self._latest_completed_summary(session, data.tenant_id, data.case_id)
            if summary is None:
                return CheckBlockingResultsOutput(blocking=False)
            blocking = any(
                str(s.polarity).upper() == WorkflowRuleVerdictPolarity.FAIL.value
                and str(s.severity).upper() in severities
                for s in summary.signals or []
            )
        return CheckBlockingResultsOutput(blocking=blocking)

    async def _latest_completed_summary(self, session, tenant_id: UUID, case_id: UUID):
        from src.workflows.infrastructure.repositories.sql_run_summary import (
            SQLWorkflowAnalysisRunSummaryRepository,
        )
        from src.workflows.infrastructure.repositories.sql_workflow_analysis_run import (
            SQLWorkflowAnalysisRunRepository,
        )

        runs = await SQLWorkflowAnalysisRunRepository(session=session).list_by_case(case_id, tenant_id)
        summary_repo = SQLWorkflowAnalysisRunSummaryRepository(session=session)
        for run in runs:  # ya viene desc por created_at
            if run.status != WorkflowAnalysisRunStatus.COMPLETED:
                continue
            summary = await summary_repo.find_by_run(run.uuid, tenant_id)
            if summary is not None:
                return summary
        return None


class SignalCaseWorkflowActivity:
    """Señal best-effort al CASE# desde el worker (la llama finalize)."""

    def __init__(self, temporal_client: TemporalClient) -> None:
        self._client = temporal_client

    @activity.defn(name=SIGNAL_CASE_WORKFLOW_ACTIVITY)
    async def signal_case_workflow(self, payload: SignalCaseWorkflowInput) -> bool:
        from src.workflows.application.workflow_cases.case_run_starter import signal_case_run

        data = SignalCaseWorkflowInput.model_validate(payload)
        return await signal_case_run(self._client, data.case_id, data.signal, data.payload)
