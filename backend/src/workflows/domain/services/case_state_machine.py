"""Máquina de estados del expediente (E4 · diseño §1).

Tabla de transiciones legales EXACTA del diseño. Un solo choke point la
consume (:class:`TransitionCaseStatus`); las fases del intérprete y el PUT de
casos pasan por él. Transición al MISMO estado = no-op legal (idempotencia
replay-safe en Temporal).
"""

from __future__ import annotations

from types import MappingProxyType

from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
from src.common.domain.exceptions._base import DomainError

# desde → hacia (frozen; ARCHIVED es terminal).
CASE_TRANSITIONS: MappingProxyType[WorkflowCaseStatus, frozenset[WorkflowCaseStatus]] = MappingProxyType(
    {
        WorkflowCaseStatus.RECEIVING: frozenset(
            {
                WorkflowCaseStatus.PROCESSING,
                WorkflowCaseStatus.FAILED,
                WorkflowCaseStatus.ARCHIVED,
            }
        ),
        WorkflowCaseStatus.PROCESSING: frozenset(
            {
                WorkflowCaseStatus.NEEDS_CLARIFICATION,
                WorkflowCaseStatus.NEEDS_REVIEW,
                WorkflowCaseStatus.ANALYZING,
                WorkflowCaseStatus.COMPLETED,
                WorkflowCaseStatus.FAILED,
                WorkflowCaseStatus.ARCHIVED,
            }
        ),
        WorkflowCaseStatus.NEEDS_CLARIFICATION: frozenset(
            {
                WorkflowCaseStatus.PROCESSING,
                WorkflowCaseStatus.FAILED,
                WorkflowCaseStatus.ARCHIVED,
            }
        ),
        WorkflowCaseStatus.NEEDS_REVIEW: frozenset(
            {
                WorkflowCaseStatus.PROCESSING,
                WorkflowCaseStatus.ANALYZING,
                WorkflowCaseStatus.REVIEW_L1,
                # E5 · §3.1: L1 skipped (by_exception) ⇒ directo a L2.
                WorkflowCaseStatus.REVIEW_L2,
                WorkflowCaseStatus.COMPLETED,
                WorkflowCaseStatus.REJECTED,
                WorkflowCaseStatus.FAILED,
                WorkflowCaseStatus.ARCHIVED,
            }
        ),
        WorkflowCaseStatus.ANALYZING: frozenset(
            {
                WorkflowCaseStatus.NEEDS_REVIEW,
                # E5 · §3.1: el gate staged entra directo al stage activado.
                WorkflowCaseStatus.REVIEW_L1,
                WorkflowCaseStatus.REVIEW_L2,
                WorkflowCaseStatus.COMPLETED,
                WorkflowCaseStatus.FAILED,
                WorkflowCaseStatus.ARCHIVED,
            }
        ),
        WorkflowCaseStatus.REVIEW_L1: frozenset(
            {
                WorkflowCaseStatus.REVIEW_L2,
                # E5 · §3.1: aprobación final (L2 skipped) reanuda el tail.
                WorkflowCaseStatus.PROCESSING,
                WorkflowCaseStatus.COMPLETED,
                WorkflowCaseStatus.REJECTED,
                WorkflowCaseStatus.FAILED,
                WorkflowCaseStatus.ARCHIVED,
            }
        ),
        WorkflowCaseStatus.REVIEW_L2: frozenset(
            {
                # E5 · §3.1: aprobación final reanuda el tail (output/deliver).
                WorkflowCaseStatus.PROCESSING,
                WorkflowCaseStatus.COMPLETED,
                WorkflowCaseStatus.REJECTED,
                WorkflowCaseStatus.FAILED,
                WorkflowCaseStatus.ARCHIVED,
            }
        ),
        WorkflowCaseStatus.COMPLETED: frozenset({WorkflowCaseStatus.ARCHIVED}),
        WorkflowCaseStatus.REJECTED: frozenset({WorkflowCaseStatus.ARCHIVED}),
        WorkflowCaseStatus.FAILED: frozenset({WorkflowCaseStatus.ARCHIVED}),
        WorkflowCaseStatus.ARCHIVED: frozenset(),
    }
)

# E5 · fan-out: estados terminales — al entrar un child aquí, el choke point
# evalúa el auto-cierre del padre (``maybe_complete_parent``).
TERMINAL_CASE_STATUSES: frozenset[WorkflowCaseStatus] = frozenset(
    {
        WorkflowCaseStatus.COMPLETED,
        WorkflowCaseStatus.REJECTED,
        WorkflowCaseStatus.FAILED,
        WorkflowCaseStatus.ARCHIVED,
    }
)


class IllegalCaseTransitionError(DomainError):
    def __init__(self, from_status: WorkflowCaseStatus, to_status: WorkflowCaseStatus):
        super().__init__(
            code="case.illegal_transition",
            message=f"Illegal case transition: {from_status.value} → {to_status.value}",
            status_code=409,
            context={"from": from_status.value, "to": to_status.value},
        )


def can_transition(from_status: WorkflowCaseStatus, to_status: WorkflowCaseStatus) -> bool:
    """Transición al mismo estado = no-op legal (replay-safe)."""
    if from_status == to_status:
        return True
    return to_status in CASE_TRANSITIONS.get(from_status, frozenset())


def assert_transition(from_status: WorkflowCaseStatus, to_status: WorkflowCaseStatus) -> None:
    if not can_transition(from_status, to_status):
        raise IllegalCaseTransitionError(from_status, to_status)
