"""Activity: transición de estado del expediente (E4 · diseño §1).

Envuelve :class:`TransitionCaseStatus` (máquina de estados + persistencia +
case_event ``status.changed``) para que las fases case-scope del intérprete
muevan el status con UNA activity. Una transición ilegal es un error de
programación de la fase ⇒ ``ApplicationError`` no reintentable
(type="case.illegal_transition"). Transición al mismo estado ⇒ no-op
(``changed=False``) — seguro ante retries/replays.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity
from temporalio.exceptions import ApplicationError

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.case_transition import (
    TransitionCaseStatusInput,
    TransitionCaseStatusOutput,
)
from src.common.domain.enums.workflow_cases import WorkflowCaseStatus

logger = get_logger(__name__)

TRANSITION_CASE_STATUS_ACTIVITY = "transition_case_status"


class TransitionCaseStatusActivity:
    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    @activity.defn(name="transition_case_status")
    async def transition_case_status(
        self, payload: TransitionCaseStatusInput
    ) -> TransitionCaseStatusOutput:
        from src.workflows.application.workflow_cases.transition import TransitionCaseStatus
        from src.workflows.domain.services.case_state_machine import IllegalCaseTransitionError
        from src.workflows.infrastructure.repositories.sql_case_event import SQLCaseEventRepository
        from src.workflows.infrastructure.repositories.sql_workflow_case import (
            SQLWorkflowCaseRepository,
        )

        data = TransitionCaseStatusInput.model_validate(payload)
        to_status = WorkflowCaseStatus.from_value(data.to_status)
        if to_status is None:
            raise ApplicationError(
                f"unknown case status: {data.to_status!r}",
                type="case.unknown_status",
                non_retryable=True,
            )
        async with self._session_maker() as session:
            try:
                result = await TransitionCaseStatus(
                    tenant_id=data.tenant_id,
                    case_id=data.case_id,
                    to_status=to_status,
                    case_repository=SQLWorkflowCaseRepository(session),
                    case_event_repository=SQLCaseEventRepository(session),
                    reason=data.reason,
                    actor=data.actor,
                ).execute()
            except IllegalCaseTransitionError as exc:
                raise ApplicationError(
                    exc.message,
                    type="case.illegal_transition",
                    non_retryable=True,
                ) from exc
        logger.info(
            "case.status_transitioned",
            case_id=str(data.case_id),
            to_status=to_status.value,
            changed=result.changed,
        )
        return TransitionCaseStatusOutput(
            case_id=data.case_id,
            status=result.case.status.value,
            changed=result.changed,
        )
