"""E5 · W1: roundtrip de `parent_case_id` en SQLWorkflowCaseRepository.

Gotcha vigente: columna nueva ⇒ create() Y update() (update persiste la
entidad COMPLETA).
"""

from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.infrastructure.repositories.sql_workflow_case import (
    SQLWorkflowCaseRepository,
)


@pytest.fixture
def case_repo(async_session):
    return SQLWorkflowCaseRepository(session=async_session)


def _build_child_case(tenant_orm, workflow_orm, parent_case_id=None) -> WorkflowCase:
    return WorkflowCase(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        name=f"Child {uuid4().hex[:6]}",
        parent_case_id=parent_case_id,
    )


async def test_create__persists_parent_case_id(case_repo, tenant_orm, workflow_orm, case_orm):
    child = _build_child_case(tenant_orm, workflow_orm, parent_case_id=case_orm.uuid)

    created = await case_repo.create(child)

    expect(created.parent_case_id).to(equal(case_orm.uuid))

    found = await case_repo.find_by_id(child.uuid, tenant_orm.uuid)
    expect(found.parent_case_id).to(equal(case_orm.uuid))


async def test_create__without_parent_case_id_is_none(case_repo, tenant_orm, workflow_orm):
    case = _build_child_case(tenant_orm, workflow_orm)

    created = await case_repo.create(case)

    expect(created.parent_case_id).to(be_none)


async def test_update__persists_parent_case_id(case_repo, tenant_orm, workflow_orm, case_orm):
    child = _build_child_case(tenant_orm, workflow_orm, parent_case_id=case_orm.uuid)
    created = await case_repo.create(child)

    created.name = "Child renombrado"
    updated = await case_repo.update(created)

    expect(updated.name).to(equal("Child renombrado"))
    expect(updated.parent_case_id).to(equal(case_orm.uuid))


# ─── E5 · W2: queries de children (fan-out) ──────────────────────────────────


async def _seed_children(case_repo, tenant_orm, workflow_orm, case_orm, statuses: list[str]):
    from src.common.domain.enums.workflow_cases import WorkflowCaseStatus

    children = []
    for status in statuses:
        child = _build_child_case(tenant_orm, workflow_orm, parent_case_id=case_orm.uuid)
        child.status = WorkflowCaseStatus(status)
        children.append(await case_repo.create(child))
    return children


async def test_count_children_by_status__groups_by_status(
    case_repo, tenant_orm, workflow_orm, case_orm
):
    await _seed_children(
        case_repo, tenant_orm, workflow_orm, case_orm, ["COMPLETED", "COMPLETED", "PROCESSING"]
    )

    counts = await case_repo.count_children_by_status(case_orm.uuid, tenant_orm.uuid)

    expect(counts).to(equal({"COMPLETED": 2, "PROCESSING": 1}))


async def test_count_children_by_status__without_children_is_empty(
    case_repo, tenant_orm, case_orm
):
    counts = await case_repo.count_children_by_status(case_orm.uuid, tenant_orm.uuid)

    expect(counts).to(equal({}))


async def test_list_children__returns_only_children_in_creation_order(
    case_repo, tenant_orm, workflow_orm, case_orm
):
    children = await _seed_children(
        case_repo, tenant_orm, workflow_orm, case_orm, ["PROCESSING", "PROCESSING"]
    )
    # Caso suelto del mismo workflow: jamás aparece como child.
    await case_repo.create(_build_child_case(tenant_orm, workflow_orm))

    listed = await case_repo.list_children(case_orm.uuid, tenant_orm.uuid)

    expect([c.uuid for c in listed]).to(equal([c.uuid for c in children]))
    for child in listed:
        expect(child.parent_case_id).to(equal(case_orm.uuid))


async def test_filter_paginated__parent_case_id_filters_children(
    case_repo, tenant_orm, workflow_orm, case_orm
):
    from src.workflows.domain.filters.workflow_case import WorkflowCaseFilters

    children = await _seed_children(
        case_repo, tenant_orm, workflow_orm, case_orm, ["PROCESSING"]
    )
    await case_repo.create(_build_child_case(tenant_orm, workflow_orm))  # suelto

    page = await case_repo.filter_paginated(
        workflow_orm.uuid,
        tenant_orm.uuid,
        WorkflowCaseFilters(parent_case_id=str(case_orm.uuid)),
    )

    expect([c.uuid for c in page.items]).to(equal([children[0].uuid]))
