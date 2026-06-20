"""Fixtures del módulo staff (E5 · ADR 0001)."""

from uuid import uuid4

import pytest

from src.common.database.models.human_task import HumanTaskORM
from src.common.database.models.staff_user import StaffUserORM
from src.common.database.models.tenants.tenant import TenantORM
from src.common.database.models.user import UserORM


@pytest.fixture
async def user_orm(async_session):
    user = UserORM(
        uuid=uuid4(),
        username=f"staffuser-{uuid4().hex[:8]}",
        password="hashed",
    )
    async_session.add(user)
    await async_session.flush()
    return user


@pytest.fixture
async def tenant_orm(async_session, user_orm):
    tenant = TenantORM(
        uuid=uuid4(),
        owner_id=user_orm.uuid,
        name="Tenant A",
        slug=f"tenant-a-{uuid4().hex[:8]}",
        status="ACTIVE",
    )
    async_session.add(tenant)
    await async_session.flush()
    return tenant


@pytest.fixture
async def other_tenant_orm(async_session, user_orm):
    tenant = TenantORM(
        uuid=uuid4(),
        owner_id=user_orm.uuid,
        name="Tenant B",
        slug=f"tenant-b-{uuid4().hex[:8]}",
        status="ACTIVE",
    )
    async_session.add(tenant)
    await async_session.flush()
    return tenant


@pytest.fixture
async def staff_user_orm(async_session, user_orm):
    staff = StaffUserORM(
        uuid=uuid4(),
        user_id=user_orm.uuid,
        role="staff_analyst_l1",
        status="active",
    )
    async_session.add(staff)
    await async_session.flush()
    return staff


def make_l1_task_orm(tenant_id, **overrides) -> HumanTaskORM:
    """Tarea del alcance staff: stage=review_l1 + INTERNAL_QUEUE + pending."""
    defaults = dict(
        uuid=uuid4(),
        tenant_id=tenant_id,
        task_key=f"run-{uuid4().hex[:10]}:human_review:review_l1",
        kind="approval",
        status="pending",
        assignee_mode="internal_queue",
        audience="doxiq_analyst",
        stage="review_l1",
        payload={},
    )
    defaults.update(overrides)
    return HumanTaskORM(**defaults)
