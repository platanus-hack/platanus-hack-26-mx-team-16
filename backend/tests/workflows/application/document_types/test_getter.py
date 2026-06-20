from datetime import UTC, datetime
from uuid import uuid4

import pytest
from expects import be_a, equal, expect

from src.common.domain.exceptions.processing import DocumentTypeNotFoundError
from src.common.domain.models.processing.document_type import DocumentType
from src.workflows.application.document_types.getter import DocumentTypeGetter


@pytest.fixture
def document_type(tenant_id):
    return DocumentType(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=uuid4(),
        name="Invoice",
        slug="invoice",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


async def test_execute__returns_document_type(tenant_id, document_type, document_type_repository):
    document_type_repository.find_by_id.return_value = document_type

    use_case = DocumentTypeGetter(
        document_type_id=document_type.uuid,
        tenant_id=tenant_id,
        document_type_repository=document_type_repository,
    )
    result = await use_case.execute()

    expect(result).to(be_a(DocumentType))
    expect(result.uuid).to(equal(document_type.uuid))
    document_type_repository.find_by_id.assert_called_once_with(document_type.uuid, tenant_id)


async def test_execute__backfills_missing_slug(tenant_id, document_type_repository):
    legacy = DocumentType(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=uuid4(),
        name="Cédula de Identidad",
        slug=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_type_repository.find_by_id.return_value = legacy
    document_type_repository.list_slugs_by_workflow.return_value = set()
    document_type_repository.update.side_effect = lambda dt: dt

    use_case = DocumentTypeGetter(
        document_type_id=legacy.uuid,
        tenant_id=tenant_id,
        document_type_repository=document_type_repository,
    )
    result = await use_case.execute()

    expect(result.slug).to(equal("cedula_de_identidad"))
    document_type_repository.update.assert_called_once()


async def test_execute__backfilled_slug_is_disambiguated(tenant_id, document_type_repository):
    legacy = DocumentType(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=uuid4(),
        name="Cedula",
        slug=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    document_type_repository.find_by_id.return_value = legacy
    document_type_repository.list_slugs_by_workflow.return_value = {"cedula"}
    document_type_repository.update.side_effect = lambda dt: dt

    use_case = DocumentTypeGetter(
        document_type_id=legacy.uuid,
        tenant_id=tenant_id,
        document_type_repository=document_type_repository,
    )
    result = await use_case.execute()

    expect(result.slug).to(equal("cedula_1"))


async def test_execute__skips_update_when_slug_already_set(tenant_id, document_type, document_type_repository):
    document_type_repository.find_by_id.return_value = document_type

    use_case = DocumentTypeGetter(
        document_type_id=document_type.uuid,
        tenant_id=tenant_id,
        document_type_repository=document_type_repository,
    )
    await use_case.execute()

    document_type_repository.update.assert_not_called()


async def test_execute__not_found_raises(tenant_id, document_type_repository):
    document_type_repository.find_by_id.return_value = None

    use_case = DocumentTypeGetter(
        document_type_id=uuid4(),
        tenant_id=tenant_id,
        document_type_repository=document_type_repository,
    )

    with pytest.raises(DocumentTypeNotFoundError):
        await use_case.execute()
