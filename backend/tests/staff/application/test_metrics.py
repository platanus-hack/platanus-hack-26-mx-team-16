"""E6 §3.5: GetStaffMetrics — agregados QA cross-tenant (solo staff_admin)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from expects import equal, expect

from src.staff.application.metrics import GetStaffMetrics
from src.staff.domain.exceptions import StaffAdminRequiredError
from src.staff.domain.models.staff_user import StaffRole, StaffUser

_TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
_TENANT_B = UUID("22222222-2222-2222-2222-222222222222")


def _staff(role: StaffRole = StaffRole.STAFF_ADMIN) -> StaffUser:
    return StaffUser(uuid=uuid4(), user_id=uuid4(), role=role)


class _FakeCaseEventRepo:
    def __init__(self, rows):
        self._rows = rows
        self.called_with = None

    async def create(self, event):  # pragma: no cover — no usado aquí
        return event

    async def list_by_case(self, *a, **k):  # pragma: no cover
        return []

    async def count_by_type_since(self, types, since, tenant_id=None):
        self.called_with = (types, since, tenant_id)
        return self._rows


async def test_metrics__requires_staff_admin():
    repo = _FakeCaseEventRepo([])
    with pytest.raises(StaffAdminRequiredError):
        await GetStaffMetrics(actor=_staff(StaffRole.STAFF_ANALYST_L1), repository=repo).execute()


async def test_metrics__aggregates_totals_by_tenant_and_by_actor():
    rows = [
        (_TENANT_A, "qa.passed", "staff:a", 3),
        (_TENANT_A, "qa.failed", "staff:b", 1),
        (_TENANT_B, "qa.passed", "staff:a", 2),
        (_TENANT_A, "review.approved", "user:x", 4),
    ]
    repo = _FakeCaseEventRepo(rows)

    metrics = await GetStaffMetrics(actor=_staff(), repository=repo).execute()

    expect(metrics.totals["qa.passed"]).to(equal(5))
    expect(metrics.totals["qa.failed"]).to(equal(1))
    expect(metrics.totals["review.approved"]).to(equal(4))
    # Por tenant: A acumula 3 qa.passed; B acumula 2.
    expect(metrics.by_tenant[str(_TENANT_A)]["qa.passed"]).to(equal(3))
    expect(metrics.by_tenant[str(_TENANT_B)]["qa.passed"]).to(equal(2))
    # Por actor: staff:a suma qa.passed cross-tenant.
    expect(metrics.by_actor["staff:a"]["qa.passed"]).to(equal(5))
    expect(metrics.by_actor["staff:b"]["qa.failed"]).to(equal(1))


async def test_metrics__defaults_to_30_day_window():
    repo = _FakeCaseEventRepo([])

    await GetStaffMetrics(actor=_staff(), repository=repo).execute()

    _types, since, tenant_id = repo.called_with
    expect(tenant_id).to(equal(None))
    # La ventana por defecto está ~30 días atrás (con margen de minutos).
    delta = datetime.now(UTC) - since
    expect(timedelta(days=29) < delta < timedelta(days=31)).to(equal(True))


async def test_metrics__passes_tenant_filter_through():
    repo = _FakeCaseEventRepo([])

    await GetStaffMetrics(actor=_staff(), repository=repo, tenant_id=_TENANT_A).execute()

    _types, _since, tenant_id = repo.called_with
    expect(tenant_id).to(equal(_TENANT_A))


async def test_metrics__none_actor_buckets_as_system():
    rows = [(_TENANT_A, "qa.sampled", None, 2)]
    repo = _FakeCaseEventRepo(rows)

    metrics = await GetStaffMetrics(actor=_staff(), repository=repo).execute()

    expect(metrics.by_actor["system"]["qa.sampled"]).to(equal(2))
