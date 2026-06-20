"""Helpers de workflow para mover el estado del caso desde las fases (E4 · §1).

Corren DENTRO del sandbox de Temporal: solo ``workflow.execute_activity`` y
datos deterministas. La transición usa el choke point
``transition_case_status``; una transición ilegal (carrera con la UI, re-runs
sobre casos COMPLETED…) se loggea y NO tumba el run — el estado del caso es
señalización, no control de flujo del pipeline.
"""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from src.common.domain.entities.workflows.case_runtime import AppendCaseEventInput
    from src.common.domain.entities.workflows.case_transition import TransitionCaseStatusInput
    from src.workflows.application.pipelines.runtime import PipelineState
    from src.workflows.presentation.workflows.base import DEFAULT_RETRY_POLICY

TRANSITION_CASE_STATUS_ACTIVITY = "transition_case_status"
APPEND_CASE_EVENT_ACTIVITY = "append_case_event"


def case_context(state: PipelineState):
    """(tenant_id, workflow_id, case_id) o None si la fase debe skipear."""
    data = state.data
    if not data.persist or data.case_id is None or data.tenant_id is None or data.workflow_id is None:
        return None
    return data.tenant_id, data.workflow_id, data.case_id


async def transition_case(state: PipelineState, to_status: str, reason: str | None = None) -> bool:
    """Transición best-effort. ``False`` si no aplicó (sin caso, ilegal, error)."""
    context = case_context(state)
    if context is None:
        return False
    tenant_id, _workflow_id, case_id = context
    try:
        await workflow.execute_activity(
            TRANSITION_CASE_STATUS_ACTIVITY,
            TransitionCaseStatusInput(
                tenant_id=tenant_id,
                case_id=case_id,
                to_status=to_status,
                reason=reason,
                actor="system",
            ),
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        return True
    except Exception:
        workflow.logger.warning(
            f"case.transition_skipped case_id={case_id} to={to_status} reason={reason}"
        )
        return False


async def append_case_event(
    state: PipelineState,
    event_type: str,
    payload: dict | None = None,
    dedupe_key: str | None = None,
) -> bool:
    """Append best-effort al timeline del caso.

    ``dedupe_key`` (estable por run+fase+evento) evita filas duplicadas cuando
    la activity se reintenta tras un éxito no confirmado por el server.
    """
    context = case_context(state)
    if context is None:
        return False
    tenant_id, _workflow_id, case_id = context
    try:
        await workflow.execute_activity(
            APPEND_CASE_EVENT_ACTIVITY,
            AppendCaseEventInput(
                tenant_id=tenant_id,
                case_id=case_id,
                type=event_type,
                payload=payload or {},
                dedupe_key=dedupe_key,
            ),
            start_to_close_timeout=timedelta(seconds=15),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        return True
    except Exception:
        workflow.logger.warning(f"case.event_append_failed case_id={case_id} type={event_type}")
        return False
