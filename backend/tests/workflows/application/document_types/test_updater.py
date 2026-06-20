from datetime import UTC, datetime
from uuid import uuid4

import pytest
from expects import be_a, be_false, be_none, be_true, equal, expect

from src.workflows.application.document_types.updater import (
    DocumentTypeUpdateOutcome,
    DocumentTypeUpdater,
)
from src.common.domain.models.processing.document_type import DocumentType
from src.common.domain.exceptions.processing import DocumentTypeNotFoundError


SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "patientName": {"type": "string", "description": "Nombre del Paciente"},
    },
    "required": ["patientName"],
}


@pytest.fixture
def existing_document_type(tenant_id):
    return DocumentType(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=uuid4(),
        name="Original Name",
        description="Original desc",
        is_shareable=False,
        slug="original_name",
        fields=None,
        current_version=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def use_case(tenant_id, existing_document_type, document_type_repository):
    document_type_repository.find_by_id.return_value = existing_document_type
    document_type_repository.update.side_effect = lambda dt: dt
    document_type_repository.list_slugs_by_workflow.return_value = set()
    return DocumentTypeUpdater(
        document_type_id=existing_document_type.uuid,
        tenant_id=tenant_id,
        document_type_repository=document_type_repository,
    )


async def test_execute__updates_name(use_case, document_type_repository):
    use_case.name = "New Name"

    outcome = await use_case.execute()

    expect(outcome).to(be_a(DocumentTypeUpdateOutcome))
    expect(outcome.document_type).to(be_a(DocumentType))
    expect(outcome.document_type.name).to(equal("New Name"))


async def test_execute__slug_is_stable_on_rename(use_case, document_type_repository):
    use_case.name = "Cedula"

    outcome = await use_case.execute()

    expect(outcome.document_type.slug).to(equal("original_name"))
    document_type_repository.list_slugs_by_workflow.assert_not_called()


async def test_execute__backfills_slug_only_when_missing(use_case, existing_document_type):
    existing_document_type.slug = None

    outcome = await use_case.execute()

    expect(outcome.document_type.slug).to(equal("original_name"))


async def test_execute__rename_alone_does_not_create_version(use_case, document_type_repository):
    use_case.name = "New Name"

    outcome = await use_case.execute()

    expect(outcome.created_new_version).to(be_false)
    expect(outcome.new_version).to(be_none)
    expect(outcome.document_type.current_version).to(equal(1))
    document_type_repository.add_version.assert_not_called()


async def test_execute__fields_change_creates_immutable_version(use_case, document_type_repository):
    use_case.fields = SAMPLE_SCHEMA

    outcome = await use_case.execute()

    expect(outcome.created_new_version).to(be_true)
    expect(outcome.new_version).to(equal(2))
    expect(outcome.document_type.current_version).to(equal(2))
    document_type_repository.add_version.assert_called_once()
    version = document_type_repository.add_version.call_args.args[0]
    expect(version.document_type_id).to(equal(outcome.document_type.uuid))
    expect(version.version).to(equal(2))
    expect(version.fields).to(equal(SAMPLE_SCHEMA))


async def test_execute__validation_rules_change_creates_version(use_case, document_type_repository):
    use_case.validation_rules = [
        {"id": "v1", "name": "Check", "prompt": "Verifica algo", "enabled": True}
    ]

    outcome = await use_case.execute()

    expect(outcome.created_new_version).to(be_true)
    expect(outcome.new_version).to(equal(2))
    document_type_repository.add_version.assert_called_once()


async def test_execute__identical_fields_do_not_create_version(
    use_case, existing_document_type, document_type_repository
):
    existing_document_type.fields = SAMPLE_SCHEMA
    use_case.fields = SAMPLE_SCHEMA

    outcome = await use_case.execute()

    expect(outcome.created_new_version).to(be_false)
    document_type_repository.add_version.assert_not_called()


async def test_execute__clear_fields_creates_version(
    use_case, existing_document_type, document_type_repository
):
    existing_document_type.fields = SAMPLE_SCHEMA
    use_case.clear_fields = True

    outcome = await use_case.execute()

    expect(outcome.document_type.fields).to(be_none)
    expect(outcome.created_new_version).to(be_true)
    expect(outcome.new_version).to(equal(2))


async def test_execute__updates_fields(use_case):
    use_case.fields = SAMPLE_SCHEMA

    outcome = await use_case.execute()

    expect(outcome.document_type.fields).to(equal(SAMPLE_SCHEMA))


async def test_execute__preserves_existing_fields_when_not_set(use_case):
    use_case.name = "Updated"

    outcome = await use_case.execute()

    expect(outcome.document_type.description).to(equal("Original desc"))
    expect(outcome.document_type.fields).to(equal(None))


async def test_execute__not_found_raises(tenant_id, document_type_repository):
    document_type_repository.find_by_id.return_value = None

    use_case = DocumentTypeUpdater(
        document_type_id=uuid4(),
        tenant_id=tenant_id,
        document_type_repository=document_type_repository,
    )

    with pytest.raises(DocumentTypeNotFoundError):
        await use_case.execute()
