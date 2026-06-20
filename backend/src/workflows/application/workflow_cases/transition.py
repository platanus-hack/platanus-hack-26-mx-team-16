"""Choke point único de cambio de estado del expediente (E4 · diseño §1).

:class:`TransitionCaseStatus` (1) valida la legalidad contra la máquina de
estados, (2) persiste el status y (3) appendea ``case_events``
(``status.changed`` + payload {from, to, reason?}). Transición al MISMO
estado = no-op silencioso (idempotencia replay-safe — Temporal puede
reintentar la activity). Los webhooks NO se emiten aquí: los emiten las
fases que tienen el contexto rico (W2a).

E5 · fan-out (§2.2): al entrar un caso CON ``parent_case_id`` a estado
terminal, el choke point evalúa :func:`maybe_complete_parent` — si ya no
quedan hermanos no-terminales, el padre transiciona PROCESSING→COMPLETED y
appendea ``children.completed`` ({total, byStatus}, dedupe). La carrera entre
los dos últimos hermanos es benigna: la transición repetida al mismo estado es
no-op legal y el ``dedupe_key`` absorbe el evento doble.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.common.application.logging import get_logger
from src.common.domain.enums.workflow_cases import WorkflowCaseStatus
from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.domain.models.case_event import CaseEvent
from src.workflows.domain.repositories.case_event import CaseEventRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.services.case_state_machine import (
    TERMINAL_CASE_STATUSES,
    assert_transition,
    can_transition,
)

logger = get_logger(__name__)

STATUS_CHANGED_EVENT = "status.changed"
CHILDREN_COMPLETED_EVENT = "children.completed"
# C3: el padre quedó RECEIVING (la señal ``case_split`` se perdió / el último
# child terminó antes de que el CASE# del padre la procesara). Recuperamos el
# limbo con RECEIVING→PROCESSING antes de cerrarlo — ambas transiciones legales.
CHILDREN_COMPLETED_RECOVERY_REASON = "children.completed.recovery"


@dataclass
class TransitionCaseStatusResult:
    case: WorkflowCase
    changed: bool


@dataclass
class TransitionCaseStatus(UseCase):
    tenant_id: UUID
    case_id: UUID
    to_status: WorkflowCaseStatus
    case_repository: WorkflowCaseRepository
    case_event_repository: CaseEventRepository
    reason: str | None = None
    actor: str | None = None

    async def execute(self) -> TransitionCaseStatusResult:
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if case is None:
            raise CaseNotFoundError(str(self.case_id))

        if case.status == self.to_status:
            # No-op legal (idempotencia replay-safe): ni persiste ni appendea.
            return TransitionCaseStatusResult(case=case, changed=False)

        assert_transition(case.status, self.to_status)

        from_status = case.status
        case.status = self.to_status
        updated = await self.case_repository.update(case)

        payload: dict = {"from": from_status.value, "to": self.to_status.value}
        if self.reason:
            payload["reason"] = self.reason
        await self.case_event_repository.create(
            CaseEvent(
                uuid=uuid4(),
                tenant_id=self.tenant_id,
                case_id=self.case_id,
                type=STATUS_CHANGED_EVENT,
                payload=payload,
                actor=self.actor,
            )
        )

        # E5 · fan-out: un child que entra a terminal puede cerrar al padre.
        if updated.parent_case_id is not None and self.to_status in TERMINAL_CASE_STATUSES:
            try:
                await maybe_complete_parent(
                    tenant_id=self.tenant_id,
                    parent_case_id=updated.parent_case_id,
                    case_repository=self.case_repository,
                    case_event_repository=self.case_event_repository,
                )
            except Exception:  # noqa: BLE001 — el cierre del padre jamás rompe la transición del child
                logger.exception(
                    "case.parent_completion_failed",
                    parent_case_id=str(updated.parent_case_id),
                    child_case_id=str(self.case_id),
                )
        return TransitionCaseStatusResult(case=updated, changed=True)


async def maybe_complete_parent(
    *,
    tenant_id: UUID,
    parent_case_id: UUID,
    case_repository: WorkflowCaseRepository,
    case_event_repository: CaseEventRepository,
) -> bool:
    """Auto-cierre del padre (E5 §2.2): 0 hermanos no-terminales ⇒ COMPLETED.

    Idempotente y race-safe: si dos hermanos terminan a la vez, el segundo ve
    al padre ya COMPLETED (no-op) y el ``dedupe_key`` absorbe el evento doble.
    Devuelve True si el padre quedó (o ya estaba) cerrado por sus children.
    """
    counts = await case_repository.count_children_by_status(parent_case_id, tenant_id)
    total = sum(counts.values())
    if total == 0:
        return False
    terminal_values = {status.value for status in TERMINAL_CASE_STATUSES}
    non_terminal = sum(n for status_value, n in counts.items() if status_value not in terminal_values)
    if non_terminal > 0:
        return False

    parent = await case_repository.find_by_id(parent_case_id, tenant_id)
    if parent is None:
        return False
    if parent.status != WorkflowCaseStatus.COMPLETED:
        # C3: padre varado en RECEIVING (señal ``case_split`` perdida o último
        # child terminado antes de que el CASE# del padre la procesara) —
        # RECEIVING→COMPLETED es ilegal. Recuperamos el limbo con
        # RECEIVING→PROCESSING (ambas legales) para que el cierre nunca se pierda.
        if parent.status == WorkflowCaseStatus.RECEIVING:
            await TransitionCaseStatus(
                tenant_id=tenant_id,
                case_id=parent_case_id,
                to_status=WorkflowCaseStatus.PROCESSING,
                case_repository=case_repository,
                case_event_repository=case_event_repository,
                reason=CHILDREN_COMPLETED_RECOVERY_REASON,
                actor="system",
            ).execute()
            parent = await case_repository.find_by_id(parent_case_id, tenant_id)
            if parent is None:
                return False
        if not can_transition(parent.status, WorkflowCaseStatus.COMPLETED):
            logger.warning(
                "case.parent_completion_illegal",
                parent_case_id=str(parent_case_id),
                status=parent.status.value,
            )
            return False
        # Recursivo por construcción: si el padre tiene a su vez un padre,
        # esta transición re-evalúa el cierre del abuelo.
        await TransitionCaseStatus(
            tenant_id=tenant_id,
            case_id=parent_case_id,
            to_status=WorkflowCaseStatus.COMPLETED,
            case_repository=case_repository,
            case_event_repository=case_event_repository,
            reason=CHILDREN_COMPLETED_EVENT,
            actor="system",
        ).execute()

    try:
        await case_event_repository.create(
            CaseEvent(
                uuid=uuid4(),
                tenant_id=tenant_id,
                case_id=parent_case_id,
                type=CHILDREN_COMPLETED_EVENT,
                payload={"total": total, "byStatus": counts},
                actor="system",
                dedupe_key=f"parent:{parent_case_id}:{CHILDREN_COMPLETED_EVENT}",
            )
        )
    except Exception:  # noqa: BLE001 — carrera del dedupe (unique) entre hermanos: benigna
        logger.warning("case.children_completed_event_dupe", parent_case_id=str(parent_case_id))
    return True
