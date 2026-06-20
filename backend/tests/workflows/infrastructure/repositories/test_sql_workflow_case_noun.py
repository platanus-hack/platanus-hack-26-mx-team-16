"""case_noun roundtrip en SQLWorkflowRepository (create + update persisten el JSONB).

Gotcha vigente: update() persiste la entidad COMPLETA — el campo nuevo se setea
en create() Y update().
"""

from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.models.processing.workflow import Workflow
from src.workflows.infrastructure.repositories.sql_workflow import SQLWorkflowRepository


@pytest.fixture
def workflow_repo(async_session):
    return SQLWorkflowRepository(session=async_session)


def _workflow(tenant_orm, case_noun: dict | None = None) -> Workflow:
    return Workflow(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        name=f"W {uuid4().hex[:6]}",
        case_noun=case_noun,
    )


async def test_create__persists_case_noun(workflow_repo, tenant_orm):
    noun = {
        "es": {"one": "Pedido", "other": "Pedidos"},
        "en": {"one": "Order", "other": "Orders"},
    }
    created = await workflow_repo.create(_workflow(tenant_orm, noun))

    expect(created.case_noun).to(equal(noun))
    found = await workflow_repo.find_by_id(created.uuid, tenant_orm.uuid)
    expect(found.case_noun).to(equal(noun))


async def test_create__case_noun_defaults_none(workflow_repo, tenant_orm):
    created = await workflow_repo.create(_workflow(tenant_orm))

    expect(created.case_noun).to(be_none)


async def test_update__persists_case_noun(workflow_repo, tenant_orm):
    created = await workflow_repo.create(_workflow(tenant_orm))

    noun = {
        "es": {"one": "Expediente", "other": "Expedientes"},
        "en": {"one": "Dossier", "other": "Dossiers"},
    }
    created.case_noun = noun
    updated = await workflow_repo.update(created)

    expect(updated.case_noun).to(equal(noun))
    found = await workflow_repo.find_by_id(created.uuid, tenant_orm.uuid)
    expect(found.case_noun).to(equal(noun))
