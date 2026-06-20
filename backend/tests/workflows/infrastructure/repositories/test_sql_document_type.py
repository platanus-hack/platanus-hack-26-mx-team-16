from datetime import UTC, datetime
from uuid import uuid4

import pytest
from expects import be_a, be_none, equal, expect

from src.common.database.models.user import UserORM
from src.common.database.models.workspace import WorkflowORM
from src.common.database.models.tenants.tenant import TenantORM
from src.common.domain.models.processing.document_type import DocumentType
from src.common.domain.exceptions.processing import DocumentTypeNotFoundError


SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "patientName": {
            "type": "string",
            "description": "Nombre del Paciente",
            "x-ai-prompt": "Extrae el nombre completo del paciente",
        },
        "medications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "dosage": {"type": "string"},
                },
            },
        },
    },
    "required": ["patientName"],
}


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
def make_document_type(tenant_orm, workflow_orm):
    def _make(name="Test DocType", fields=None):
        now = datetime.now(UTC)
        return DocumentType(
            uuid=uuid4(),
            tenant_id=tenant_orm.uuid,
            workflow_id=workflow_orm.uuid,
            name=name,
            is_shareable=False,
            slug=None,
            description=None,
            fields=fields,
            created_at=now,
            updated_at=now,
        )

    return _make


async def test_create__persists_fields(document_type_repo, make_document_type):
    doc_type = make_document_type(fields=SAMPLE_SCHEMA)

    result = await document_type_repo.create(doc_type)

    expect(result).to(be_a(DocumentType))
    expect(result.fields).to(equal(SAMPLE_SCHEMA))


async def test_create__null_fields(document_type_repo, make_document_type):
    doc_type = make_document_type(fields=None)

    result = await document_type_repo.create(doc_type)

    expect(result.fields).to(be_none)


async def test_find_by_id__returns_fields(document_type_repo, make_document_type, tenant_orm):
    doc_type = make_document_type(fields=SAMPLE_SCHEMA)
    created = await document_type_repo.create(doc_type)

    found = await document_type_repo.find_by_id(created.uuid, tenant_orm.uuid)

    expect(found).not_to(be_none)
    expect(found.fields).to(equal(SAMPLE_SCHEMA))


async def test_update__sets_fields(document_type_repo, make_document_type, tenant_orm):
    doc_type = make_document_type(fields=None)
    created = await document_type_repo.create(doc_type)
    created.fields = SAMPLE_SCHEMA

    updated = await document_type_repo.update(created)

    expect(updated.fields).to(equal(SAMPLE_SCHEMA))


async def test_update__modifies_fields(document_type_repo, make_document_type, tenant_orm):
    doc_type = make_document_type(fields=SAMPLE_SCHEMA)
    created = await document_type_repo.create(doc_type)

    new_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    created.fields = new_schema

    updated = await document_type_repo.update(created)

    expect(updated.fields).to(equal(new_schema))


async def test_update__not_found_raises(document_type_repo, make_document_type):
    doc_type = make_document_type()
    doc_type.uuid = uuid4()

    with pytest.raises(DocumentTypeNotFoundError):
        await document_type_repo.update(doc_type)


async def test_find_by_id__wrong_tenant_returns_none(document_type_repo, make_document_type):
    doc_type = make_document_type(fields=SAMPLE_SCHEMA)
    created = await document_type_repo.create(doc_type)

    result = await document_type_repo.find_by_id(created.uuid, uuid4())

    expect(result).to(be_none)


async def test_list_slugs_by_workflow__returns_existing_slugs(
    document_type_repo, make_document_type, tenant_orm, workflow_orm
):
    a = make_document_type(name="Cedula")
    a.slug = "cedula"
    b = make_document_type(name="Cedula")
    b.slug = "cedula_1"
    c = make_document_type(name="Invoice")  # slug stays None
    await document_type_repo.create(a)
    await document_type_repo.create(b)
    await document_type_repo.create(c)

    slugs = await document_type_repo.list_slugs_by_workflow(workflow_orm.uuid, tenant_orm.uuid)

    expect(slugs).to(equal({"cedula", "cedula_1"}))


async def test_list_slugs_by_workflow__excludes_given_doctype(
    document_type_repo, make_document_type, tenant_orm, workflow_orm
):
    a = make_document_type(name="Cedula")
    a.slug = "cedula"
    b = make_document_type(name="Cedula")
    b.slug = "cedula_1"
    await document_type_repo.create(a)
    await document_type_repo.create(b)

    slugs = await document_type_repo.list_slugs_by_workflow(
        workflow_orm.uuid,
        tenant_orm.uuid,
        exclude_document_type_id=a.uuid,
    )

    expect(slugs).to(equal({"cedula_1"}))
