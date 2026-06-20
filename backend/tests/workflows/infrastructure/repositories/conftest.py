from uuid import uuid4

import pytest

from src.common.database.models.processing.workflow_case import WorkflowCaseORM
from src.common.database.models.processing.file_upload import DocumentORM
from src.common.database.models.tenants.tenant import TenantORM
from src.common.database.models.user import UserORM
from src.common.database.models.workspace import WorkflowORM
from src.workflows.infrastructure.repositories.sql_document_type import (
    SQLDocumentTypeRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_phase_execution import (
    SQLWorkflowPhaseExecutionRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_processing_job import (
    SQLWorkflowProcessingJobRepository,
)


@pytest.fixture
def processing_job_repo(async_session):
    return SQLWorkflowProcessingJobRepository(session=async_session)


@pytest.fixture
def phase_execution_repo(async_session):
    return SQLWorkflowPhaseExecutionRepository(session=async_session)


@pytest.fixture
def document_type_repo(async_session):
    return SQLDocumentTypeRepository(session=async_session)


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
