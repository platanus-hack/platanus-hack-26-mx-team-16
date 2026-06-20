"""Shared processing-job workflow plumbing (F1 extraction · único motor desde E1).

``PipelineInterpreterWorkflow`` drives the real-time feedback channel
(monotonic ``seq`` → ``update_workflow_processing_job_status`` → Redis publish) and
the Lambda-invocation + failure discipline through this base. That plumbing lives
here once so there is a single source of truth; the concrete workflows add
``@workflow.signal`` handlers and a ``@workflow.run`` body on top.
"""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from uuid import UUID

    from src.common.domain.entities.workflows.document_processing import (
        DocumentProcessingInput,
        InvokeLambdaInput,
    )
    from src.common.domain.enums.processing_job_events import (
        ProcessingJobEventType,
        DocumentStatus,
        JobStatus,
        JobStep,
    )
    from src.workflows.domain.events import ProcessingJobEvent
    from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
        MarkDocumentInput,
        PersistedDocumentRef,
        UpdateWorkflowProcessingJobStatusInput,
    )

DEFAULT_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=2,
)

INVOKE_LAMBDA_ACTIVITY = "invoke_lambda"
READ_S3_JSON_ACTIVITY = "read_s3_json"
PUBLISH_PROCESSING_JOB_EVENT_ACTIVITY = "publish_processing_job_event"
READ_CLASSIFIED_REFS_ACTIVITY = "read_classified_refs"
SPLIT_CLASSIFIED_DOCS_ACTIVITY = "split_classified_documents"
PERSIST_DOCUMENT_TEXTS_ACTIVITY = "persist_document_texts"
PERSIST_CLASSIFIED_DOCS_ACTIVITY = "persist_classified_documents"
UPDATE_WORKFLOW_PROCESSING_JOB_STATUS_ACTIVITY = "update_workflow_processing_job_status"
RECORD_PHASE_EXECUTION_ACTIVITY = "record_phase_execution"
MARK_DOCUMENT_STATUS_ACTIVITY = "mark_document_status"
CREATE_PROCESS_RECORD_ACTIVITY = "create_process_record"
DISPATCH_PROCESSING_JOB_WEBHOOK_ACTIVITY = "dispatch_processing_job_webhook"


class ProcessingJobWorkflowBase:
    """Mixin: seq counter, pause/cancel gating, checkpoint, lambda, failure paths.

    Concrete workflows must declare the ``cancel``/``pause``/``resume`` signals
    (they flip ``_cancel_requested`` / ``_paused``) and call :meth:`__init__`.
    """

    def __init__(self) -> None:
        self._cancel_requested: bool = False
        self._paused: bool = False
        self._seq: int = 0
        # F6: durable human/data pauses — task_key → resolution payload, filled
        # by the concrete workflow's ``task_resolved`` signal.
        self._resolved_tasks: dict[str, dict] = {}
        # F4 (quórum): task_key → lista append-only de votos (cada resolución que
        # llega), para acumular N-de-M. Replay-safe: las señales se re-aplican en
        # orden. El gate single (N=1) sigue usando ``_resolved_tasks`` (compat).
        self._votes: dict[str, list[dict]] = {}
        # E4: señales del run de caso (CASE#) — contadores monotónicos para que
        # ``await_documents`` re-evalúe sin perder señales entre iteraciones.
        self._case_docs_changed_count: int = 0
        self._case_ready_count: int = 0
        self._case_ready_requested: bool = False
        self._case_ready_force: bool = False
        # E5 · fan-out: señal ``case_split`` — el padre fue partido en children.
        self._case_split: bool = False
        # E5 · §3.3: correcciones pendientes por task_key (señal ``corrections``)
        # — colas FIFO; el stage de revisión las consume y re-analiza.
        self._pending_corrections: dict[str, list[dict]] = {}

    async def _yield_for_signals(self) -> None:
        await workflow.wait_condition(lambda: not self._paused)
        if self._cancel_requested:
            raise ApplicationError("Workflow cancelled by signal", non_retryable=True)

    async def wait_for_task(self, task_key: str) -> dict:
        """Durably block until ``task_resolved`` arrives for ``task_key`` (F6).

        Survives worker restarts: Temporal replays history and re-applies the
        signal, so the condition is met again on resume."""
        await workflow.wait_condition(lambda: task_key in self._resolved_tasks)
        return self._resolved_tasks[task_key]

    async def wait_for_task_or_corrections(self, task_key: str) -> tuple[str, dict]:
        """E5 · §3.3: bloqueo durable hasta resolución O corrección pendiente.

        Las correcciones tienen prioridad: si una aprobación llega con un
        re-analyze en vuelo (o pendiente), se procesa la corrección PRIMERO y
        la aprobación se aplica después (invariante: re-evaluar antes de
        permitir aprobar). Devuelve ``("corrections", payload)`` o
        ``("resolved", resolution)``."""
        await workflow.wait_condition(
            lambda: bool(self._pending_corrections.get(task_key))
            or task_key in self._resolved_tasks
        )
        pending = self._pending_corrections.get(task_key)
        if pending:
            return "corrections", pending.pop(0)
        return "resolved", self._resolved_tasks[task_key]

    # ── E4: señales del run de caso (await_documents) ──────────────────────
    def case_signal_marks(self) -> tuple[int, int]:
        """Marcas (docs_changed, ready) tomadas ANTES de evaluar — si llega una
        señal durante la evaluación, los contadores ya difieren y
        ``wait_for_case_signal`` retorna al instante (sin señales perdidas)."""
        return self._case_docs_changed_count, self._case_ready_count

    async def wait_for_case_signal(self, docs_seen: int, ready_seen: int) -> None:
        """Bloqueo durable hasta una señal ``case_docs_changed``/``case_ready``
        (o ``case_split``, E5) posterior a las marcas dadas."""
        await workflow.wait_condition(
            lambda: self._case_docs_changed_count != docs_seen
            or self._case_ready_count != ready_seen
            or self._case_split
        )

    async def _checkpoint(
        self,
        data: DocumentProcessingInput,
        *,
        type: ProcessingJobEventType,
        payload: dict,
        job_status: JobStatus,
        current_step: JobStep | None = None,
        document_id: UUID | None = None,
        extracted_text_key: str | None = None,
        classified_pages_key: str | None = None,
    ) -> None:
        """Bump seq, persist processing-job state, then publish to Redis."""
        await self._yield_for_signals()

        if not data.persist:
            return
        if data.workflow_id is None or data.processing_job_uuid is None:
            return

        self._seq += 1
        seq = self._seq
        ts = workflow.now()

        await workflow.execute_activity(
            UPDATE_WORKFLOW_PROCESSING_JOB_STATUS_ACTIVITY,
            UpdateWorkflowProcessingJobStatusInput(
                processing_job_uuid=data.processing_job_uuid,
                status=job_status,
                current_step=current_step,
                last_seq=seq,
                error=payload.get("error_data") if type == ProcessingJobEventType.FAILED else None,
                extracted_text_key=extracted_text_key,
                classified_pages_key=classified_pages_key,
            ),
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

        event = ProcessingJobEvent.build(
            type=type,
            seq=seq,
            ts=ts,
            workflow_id=data.workflow_id,
            processing_job_id=data.processing_job_uuid,
            workflow_case_id=data.case_id,
            document_id=document_id,
            payload=payload,
        )
        await workflow.execute_activity(
            PUBLISH_PROCESSING_JOB_EVENT_ACTIVITY,
            event,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=DEFAULT_RETRY_POLICY,
        )

    async def _invoke_lambda(
        self,
        function_name: str,
        payload: dict,
        timeout: timedelta,
        label: str,
    ) -> dict:
        return await workflow.execute_activity(
            INVOKE_LAMBDA_ACTIVITY,
            InvokeLambdaInput(function_name=function_name, payload=payload),
            start_to_close_timeout=timeout,
            retry_policy=DEFAULT_RETRY_POLICY,
            activity_id=label,
            summary=label,
        )

    async def _fail_document(
        self,
        data: DocumentProcessingInput,
        doc: PersistedDocumentRef,
        source_step: JobStep,
        err: dict,
    ) -> None:
        if data.persist:
            await workflow.execute_activity(
                MARK_DOCUMENT_STATUS_ACTIVITY,
                MarkDocumentInput(
                    document_id=doc.document_id,
                    status=DocumentStatus.FAILED,
                    error=err,
                ),
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=DEFAULT_RETRY_POLICY,
            )
        await self._checkpoint(
            data,
            type=ProcessingJobEventType.STEP_COMPLETED,
            payload={
                "status": "failed",
                "step": source_step.value,
                "error_code": err.get("error_code", "extraction.error"),
                "message": err.get("message") or str(err),
                "source_step": source_step.value,
            },
            job_status=JobStatus.PROCESSING,
            current_step=source_step,
            document_id=doc.document_id,
        )

    async def _fail_job(
        self,
        data: DocumentProcessingInput,
        source_step: JobStep,
        exc: Exception,
    ) -> None:
        await self._checkpoint(
            data,
            type=ProcessingJobEventType.FAILED,
            payload={
                "error_code": "workflow.error",
                "message": str(exc),
                "source_step": source_step.value,
                "file_name": data.file_name,
                "finished_at": workflow.now().isoformat(),
                "error_data": {"type": type(exc).__name__, "message": str(exc)},
            },
            job_status=JobStatus.FAILED,
            current_step=source_step,
        )
