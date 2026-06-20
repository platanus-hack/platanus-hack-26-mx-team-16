from datetime import UTC, datetime
from uuid import uuid4

import pytest
from expects import be_a, equal, expect

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.models.processing.document_type import DocumentType
from src.common.domain.models.processing.workflow import Workflow
from src.workflows.application.document_types.creator import DocumentTypeCreator


@pytest.fixture
def workflow(tenant_id):
    return Workflow(
        uuid=uuid4(),
        tenant_id=tenant_id,
        name="Test Workflow",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def use_case(tenant_id, workflow, document_type_repository, workflow_repository):
    workflow_repository.find_by_id.return_value = workflow
    document_type_repository.list_slugs_by_workflow.return_value = set()
    document_type_repository.create.side_effect = lambda dt: dt
    return DocumentTypeCreator(
        tenant_id=tenant_id,
        workflow_id=workflow.uuid,
        name="Cedula",
        document_type_repository=document_type_repository,
        workflow_repository=workflow_repository,
    )


async def test_execute__creates_with_auto_generated_slug(use_case):
    result = await use_case.execute()

    expect(result).to(be_a(DocumentType))
    expect(result.slug).to(equal("cedula"))


async def test_execute__appends_numeric_suffix_on_collision(use_case, document_type_repository):
    document_type_repository.list_slugs_by_workflow.return_value = {"cedula"}

    result = await use_case.execute()

    expect(result.slug).to(equal("cedula_1"))


async def test_execute__skips_taken_suffixes(use_case, document_type_repository):
    document_type_repository.list_slugs_by_workflow.return_value = {
        "cedula",
        "cedula_1",
        "cedula_2",
    }

    result = await use_case.execute()

    expect(result.slug).to(equal("cedula_3"))


async def test_execute__normalizes_accents_and_spaces(use_case, document_type_repository):
    use_case.name = "Cédula de Identidad"

    result = await use_case.execute()

    expect(result.slug).to(equal("cedula_de_identidad"))
    document_type_repository.list_slugs_by_workflow.assert_called_once_with(use_case.workflow_id, use_case.tenant_id)


async def test_execute__seals_immutable_v1_on_creation(use_case, document_type_repository):
    result = await use_case.execute()

    expect(result.current_version).to(equal(1))
    document_type_repository.add_version.assert_called_once()
    version = document_type_repository.add_version.call_args.args[0]
    expect(version.document_type_id).to(equal(result.uuid))
    expect(version.version).to(equal(1))
    expect(version.fields).to(equal(result.fields))
    expect(version.validation_rules).to(equal(result.validation_rules))


async def test_execute__workflow_not_found_raises(tenant_id, document_type_repository, workflow_repository):
    workflow_repository.find_by_id.return_value = None

    use_case = DocumentTypeCreator(
        tenant_id=tenant_id,
        workflow_id=uuid4(),
        name="Anything",
        document_type_repository=document_type_repository,
        workflow_repository=workflow_repository,
    )

    with pytest.raises(WorkflowNotFoundError):
        await use_case.execute()
