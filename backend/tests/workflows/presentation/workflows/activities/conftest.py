"""ORM fixtures for activity integration tests.

Mirrors the fixtures in `tests/workflows/infrastructure/repositories/conftest.py`
so the new live-feedback activities can be exercised against a real DB.
"""

from uuid import uuid4

import pytest

from src.common.database.models.processing.file_upload import DocumentORM
from src.common.database.models.processing.workflow_case import WorkflowCaseORM
from src.common.database.models.tenants.tenant import TenantORM
from src.common.database.models.user import UserORM
from src.common.database.models.workspace import WorkflowORM


@pytest.fixture
async def user_orm(async_session):
    user = UserORM(
        uuid=uuid4(),
        username=f"testuser-{uuid4().hex[:8]}",
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
async def case_orm(async_session, tenant_orm, workflow_orm):
    case = WorkflowCaseORM(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        name="Test Case",
    )
    async_session.add(case)
    await async_session.flush()
    return case


@pytest.fixture
async def file_orm(async_session, tenant_orm):
    document = DocumentORM(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        file_name="test.pdf",
        mime="application/pdf",
        size=1234,
        s3_key=f"tenants/{tenant_orm.uuid}/files/test-{uuid4().hex[:8]}.pdf",
    )
    async_session.add(document)
    await async_session.flush()
    return document
