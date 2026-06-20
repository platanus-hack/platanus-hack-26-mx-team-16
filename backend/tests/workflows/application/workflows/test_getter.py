from uuid import uuid4

import pytest
from expects import be_a, equal, expect

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.models.processing.workflow import Workflow
from src.workflows.application.workflows.getter import WorkflowGetter


@pytest.fixture
def workflow(tenant_id):
    return Workflow(
        uuid=uuid4(),
        tenant_id=tenant_id,
        name="Test Workflow",
    )


async def test_execute__returns_workflow(tenant_id, workflow, workflow_repository):
    workflow_repository.find_by_id.return_value = workflow

    use_case = WorkflowGetter(
        workflow_id=workflow.uuid,
        tenant_id=tenant_id,
        workflow_repository=workflow_repository,
    )
    result = await use_case.execute()

    expect(result).to(be_a(Workflow))
    expect(result.uuid).to(equal(workflow.uuid))
    workflow_repository.find_by_id.assert_called_once_with(workflow.uuid, tenant_id)


async def test_execute__not_found_raises(tenant_id, workflow_repository):
    workflow_repository.find_by_id.return_value = None

    use_case = WorkflowGetter(
        workflow_id=uuid4(),
        tenant_id=tenant_id,
        workflow_repository=workflow_repository,
    )

    with pytest.raises(WorkflowNotFoundError):
        await use_case.execute()
