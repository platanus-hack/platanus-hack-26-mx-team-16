"""Métricas QA agregadas — solo ``staff_admin`` (E6 · §3.5).

Cuenta eventos del timeline (``case_events``) cross-tenant desde una ventana
temporal y los proyecta en dos cortes: por tenant y por actor. Sirve la base del
SLA: tasa de auto-aprobación (review.skipped vs review.approved) y pass-rate de
la auditoría QA (qa.passed vs qa.failed) del modelo y del analista.

Sin tabla nueva: reusa el índice ``(tenant_id, type, created_at)`` de la
migración E6 vía ``CaseEventRepository.count_by_type_since``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from src.common.application.helpers.datetimes import utc_now
from src.common.domain.interfaces.use_case import UseCase
from src.staff.domain.exceptions import StaffAdminRequiredError
from src.staff.domain.models.staff_user import StaffRole, StaffUser
from src.workflows.domain.repositories.case_event import CaseEventRepository

# Tipos contados por el dashboard QA (E6 · §3.5).
QA_PASSED = "qa.passed"
QA_FAILED = "qa.failed"
QA_SAMPLED = "qa.sampled"
REVIEW_APPROVED = "review.approved"
REVIEW_SKIPPED = "review.skipped"
METRIC_TYPES = [QA_PASSED, QA_FAILED, QA_SAMPLED, REVIEW_APPROVED, REVIEW_SKIPPED]

DEFAULT_WINDOW_DAYS = 30


@dataclass
class StaffMetrics:
    since: datetime
    # type -> conteo total
    totals: dict[str, int] = field(default_factory=dict)
    # tenant_id (str) -> {type: conteo}
    by_tenant: dict[str, dict[str, int]] = field(default_factory=dict)
    # actor (str) -> {type: conteo}; actor None ⇒ "system"
    by_actor: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass
class GetStaffMetrics(UseCase):
    actor: StaffUser
    repository: CaseEventRepository
    since: datetime | None = None
    tenant_id: UUID | None = None

    async def execute(self) -> StaffMetrics:
        if self.actor.role is not StaffRole.STAFF_ADMIN:
            raise StaffAdminRequiredError({"role": self.actor.role.value})

        since = self.since or (utc_now() - timedelta(days=DEFAULT_WINDOW_DAYS))
        rows = await self.repository.count_by_type_since(
            types=METRIC_TYPES,
            since=since,
            tenant_id=self.tenant_id,
        )

        metrics = StaffMetrics(since=since)
        for tenant_id, event_type, actor, count in rows:
            metrics.totals[event_type] = metrics.totals.get(event_type, 0) + count
            tenant_key = str(tenant_id)
            metrics.by_tenant.setdefault(tenant_key, {})[event_type] = (
                metrics.by_tenant.setdefault(tenant_key, {}).get(event_type, 0) + count
            )
            actor_key = actor or "system"
            metrics.by_actor.setdefault(actor_key, {})[event_type] = (
                metrics.by_actor.setdefault(actor_key, {}).get(event_type, 0) + count
            )
        return metrics
