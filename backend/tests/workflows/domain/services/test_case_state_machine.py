"""E4 · diseño §1: máquina de estados del expediente.

Transiciones legales/ilegales según la tabla congelada, idempotencia
(mismo estado = no-op legal) y el error 409 ``case.illegal_transition``.
"""

from __future__ import annotations

import pytest
from expects import be_false, be_true, equal, expect

from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
from src.workflows.domain.services.case_state_machine import (
    CASE_TRANSITIONS,
    IllegalCaseTransitionError,
    assert_transition,
    can_transition,
)

S = WorkflowCaseStatus


def test_transitions_table__covers_all_states():
    expect(set(CASE_TRANSITIONS.keys())).to(equal(set(WorkflowCaseStatus)))


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (S.RECEIVING, S.PROCESSING),
        (S.RECEIVING, S.FAILED),
        (S.PROCESSING, S.NEEDS_CLARIFICATION),
        (S.PROCESSING, S.NEEDS_REVIEW),
        (S.PROCESSING, S.ANALYZING),
        (S.PROCESSING, S.COMPLETED),
        (S.NEEDS_CLARIFICATION, S.PROCESSING),
        (S.NEEDS_REVIEW, S.REVIEW_L1),
        (S.NEEDS_REVIEW, S.REJECTED),
        (S.ANALYZING, S.NEEDS_REVIEW),
        (S.ANALYZING, S.COMPLETED),
        (S.REVIEW_L1, S.REVIEW_L2),
        (S.REVIEW_L2, S.COMPLETED),
        (S.COMPLETED, S.ARCHIVED),
        (S.REJECTED, S.ARCHIVED),
        (S.FAILED, S.ARCHIVED),
    ],
)
def test_can_transition__legal(from_status, to_status):
    expect(can_transition(from_status, to_status)).to(be_true)


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (S.RECEIVING, S.ANALYZING),
        (S.RECEIVING, S.COMPLETED),
        (S.COMPLETED, S.PROCESSING),
        (S.ARCHIVED, S.PROCESSING),
        (S.ARCHIVED, S.COMPLETED),
        (S.REJECTED, S.COMPLETED),
        (S.FAILED, S.PROCESSING),
        (S.ANALYZING, S.NEEDS_CLARIFICATION),
        (S.REVIEW_L2, S.REVIEW_L1),
        (S.COMPLETED, S.REJECTED),
    ],
)
def test_can_transition__illegal(from_status, to_status):
    expect(can_transition(from_status, to_status)).to(be_false)


@pytest.mark.parametrize("status", list(WorkflowCaseStatus))
def test_can_transition__same_state_is_legal_noop(status):
    # Replay-safe: la transición al estado actual nunca es ilegal.
    expect(can_transition(status, status)).to(be_true)


def test_archived_is_terminal():
    expect(CASE_TRANSITIONS[S.ARCHIVED]).to(equal(frozenset()))


def test_assert_transition__raises_409_with_code():
    with pytest.raises(IllegalCaseTransitionError) as exc_info:
        assert_transition(S.COMPLETED, S.PROCESSING)

    expect(exc_info.value.status_code).to(equal(409))
    expect(exc_info.value.code).to(equal("case.illegal_transition"))
    expect(exc_info.value.context).to(equal({"from": "COMPLETED", "to": "PROCESSING"}))


def test_assert_transition__legal_does_not_raise():
    assert_transition(S.RECEIVING, S.PROCESSING)
    assert_transition(S.ANALYZING, S.ANALYZING)  # no-op idempotente


# ─── E5 §3.1: transiciones de la revisión multinivel ─────────────────────────


@pytest.mark.parametrize(
    ("from_status", "to_status"),
    [
        (S.ANALYZING, S.REVIEW_L1),  # el gate staged entra directo al stage
        (S.ANALYZING, S.REVIEW_L2),  # L1 skipped (by_exception)
        (S.NEEDS_REVIEW, S.REVIEW_L2),
        (S.REVIEW_L1, S.PROCESSING),  # aprobación final con L2 skipped
        (S.REVIEW_L2, S.PROCESSING),  # aprobación final reanuda el tail
        (S.REVIEW_L1, S.REVIEW_L2),  # secuencia L1 → L2 (ya existía)
        (S.REVIEW_L1, S.REJECTED),
        (S.REVIEW_L2, S.REJECTED),
    ],
)
def test_can_transition__e5_staged_review_legal(from_status, to_status):
    expect(can_transition(from_status, to_status)).to(be_true)


def test_can_transition__e5_no_l2_back_to_l1():
    # Diseño §3.1: sin vuelta L2→L1.
    expect(can_transition(S.REVIEW_L2, S.REVIEW_L1)).to(be_false)
