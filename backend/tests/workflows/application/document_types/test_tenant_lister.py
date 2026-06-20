from datetime import UTC, datetime
from uuid import uuid4

import pytest
from expects import expect, have_length

from src.common.domain.models.processing.document_type import DocumentType
from src.workflows.application.document_types.tenant_lister import (
    DocumentTypeTenantLister,
)


@pytest.fixture
def document_types(tenant_id):
    return [
        DocumentType(
            uuid=uuid4(),
            tenant_id=tenant_id,
            workflow_id=uuid4(),
            name=f"Doctype {i}",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        for i in range(3)
    ]


async def test_execute__returns_all_tenant_doctypes(tenant_id, document_types, document_type_repository):
    document_type_repository.list_by_tenant.return_value = document_types

    use_case = DocumentTypeTenantLister(
        tenant_id=tenant_id,
        document_type_repository=document_type_repository,
    )
    result = await use_case.execute()

    expect(result).to(have_length(3))
    document_type_repository.list_by_tenant.assert_called_once_with(tenant_id)
