from uuid import uuid4

import pytest

from src.common.database.models.tenants.tenant import TenantORM
from src.common.database.models.user import UserORM
from src.common.database.models.workflow_source import WorkflowSourceORM
from src.common.database.models.workspace import WorkflowORM


@pytest.fixture
async def user_orm(async_session):
    user = UserORM(uuid=uuid4(), username=f"testuser-{uuid4().hex[:8]}", password="hashed")
    async_session.add(user)
    await async_session.flush()
    return user


@pytest.fixture
async def tenant_orm(async_session, user_orm):
    tenant = TenantORM(
        uuid=uuid4(),
        owner_id=user_orm.uuid,
        name="Test Tenant",
        slug=f"test-{uuid4().hex[:8]}",
        status="ACTIVE",
    )
    async_session.add(tenant)
    await async_session.flush()
    return tenant


@pytest.fixture
async def workflow_orm(async_session, tenant_orm):
    workflow = WorkflowORM(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        name="Test Workflow",
    )
    async_session.add(workflow)
    await async_session.flush()
    return workflow


@pytest.fixture
async def source_orm(async_session, tenant_orm, workflow_orm):
    source = WorkflowSourceORM(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        provider="EMAIL",
        route_token=f"src_{uuid4().hex[:12]}",
    )
    async_session.add(source)
    await async_session.flush()
    return source
