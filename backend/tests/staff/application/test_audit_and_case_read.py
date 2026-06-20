"""E5 · W4: ListStaffAudit (gate staff_admin) y GetCaseReadOnly (404 + gate L1)."""

from uuid import UUID, uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.enums.human_tasks import HumanTaskKind, HumanTaskStatus
from src.staff.application.audit import ListStaffAudit
from src.staff.application.case_read import GetCaseReadOnly
from src.staff.domain.entities import StaffCaseAggregate
from src.staff.domain.exceptions import StaffAdminRequiredError, StaffCaseNotFoundError
from src.staff.domain.models.staff_user import StaffRole, StaffUser
from src.workflows.domain.models.human_task import HumanTask


def _staff(role: StaffRole = StaffRole.STAFF_ANALYST_L1) -> StaffUser:
    return StaffUser(uuid=uuid4(), user_id=uuid4(), role=role)


def _l1_task(case_id: UUID) -> HumanTask:
    return HumanTask(
        uuid=uuid4(),
        tenant_id=uuid4(),
        task_key="run-1:human_review:review_l1",
        kind=HumanTaskKind.APPROVAL,
        status=HumanTaskStatus.PENDING,
        stage="review_l1",
        case_id=case_id,
    )


class _FakeEventsRepo:
    def __init__(self):
        self.called_with = None

    async def list(self, **kwargs):
        self.called_with = kwargs
        return []


class _FakeReader:
    def __init__(self, aggregate):
        self._aggregate = aggregate
        self.asked_for = None

    async def get_case_aggregate(self, case_id):
        self.asked_for = case_id
        return self._aggregate


class _FakeTaskRepo:
    """Solo devuelve la tarea L1 si el case_id coincide con el ligado."""

    def __init__(self, gate_task: HumanTask | None):
        self._gate_task = gate_task
        self.asked_for = None

    async def find_l1_task_by_case(self, case_id):
        self.asked_for = case_id
        if self._gate_task is not None and self._gate_task.case_id == case_id:
            return self._gate_task
        return None


async def test_audit__analyst_is_forbidden():
    analyst = StaffUser(uuid=uuid4(), user_id=uuid4(), role=StaffRole.STAFF_ANALYST_L1)
    with pytest.raises(StaffAdminRequiredError):
        await ListStaffAudit(actor=analyst, repository=_FakeEventsRepo()).execute()


async def test_audit__admin_passes_filters_through():
    admin = StaffUser(uuid=uuid4(), user_id=uuid4(), role=StaffRole.STAFF_ADMIN)
    repo = _FakeEventsRepo()
    tenant_id = uuid4()

    await ListStaffAudit(
        actor=admin, repository=repo, tenant_id=tenant_id, action="tasks.claim", limit=10
    ).execute()

    expect(repo.called_with["tenant_id"]).to(equal(tenant_id))
    expect(repo.called_with["action"]).to(equal("tasks.claim"))
    expect(repo.called_with["limit"]).to(equal(10))


async def test_case_read__missing_case_is_404():
    # C6: el gate L1 está, pero el caso no existe en el agregado ⇒ 404.
    case_id = uuid4()
    with pytest.raises(StaffCaseNotFoundError):
        await GetCaseReadOnly(
            case_id=case_id,
            staff_user=_staff(),
            reader=_FakeReader(None),
            task_repository=_FakeTaskRepo(_l1_task(case_id)),
        ).execute()


async def test_case_read__returns_aggregate_when_l1_task_links_the_case():
    case_id = uuid4()
    aggregate = StaffCaseAggregate(case=object(), tenant_name="Tenant A")
    reader = _FakeReader(aggregate)

    result = await GetCaseReadOnly(
        case_id=case_id,
        staff_user=_staff(),
        reader=reader,
        task_repository=_FakeTaskRepo(_l1_task(case_id)),
    ).execute()

    expect(result.tenant_name).to(equal("Tenant A"))
    expect(reader.asked_for).to(equal(case_id))


async def test_case_read__no_l1_task_linked_is_404_without_loading_aggregate():
    # C6 [CRÍTICO]: caso de OTRO tenant sin tarea L1 ligada ⇒ 404 (fuga de PII
    # cross-tenant cerrada). El agregado JAMÁS se carga: el gate corta antes.
    case_id = uuid4()
    reader = _FakeReader(StaffCaseAggregate(case=object(), tenant_name="Tenant B"))
    task_repo = _FakeTaskRepo(gate_task=None)

    with pytest.raises(StaffCaseNotFoundError):
        await GetCaseReadOnly(
            case_id=case_id,
            staff_user=_staff(),
            reader=reader,
            task_repository=task_repo,
        ).execute()

    expect(task_repo.asked_for).to(equal(case_id))
    expect(reader.asked_for).to(be_none)  # nunca se tocó el caso ⇒ sin fuga
