"""E5 · W1: roundtrip de `verification`/`parent_document_id`/`SPLIT_CHILD`
en SQLWorkflowDocumentRepository (create Y update — gotcha entidad completa).
"""

from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.enums.workflows import WorkflowDocumentSource, WorkflowDocumentStatus
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.infrastructure.repositories.sql_document_repository import (
    SQLWorkflowDocumentRepository,
)


@pytest.fixture
def workflow_document_repo(async_session):
    return SQLWorkflowDocumentRepository(session=async_session)


def _build_document(tenant_orm, workflow_orm, case_orm, **overrides) -> WorkflowDocument:
    base = dict(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        case_id=case_orm.uuid,
        file_name=f"doc-{uuid4().hex[:6]}.pdf",
        status=WorkflowDocumentStatus.EXTRACTED,
        source=WorkflowDocumentSource.SINGLE,
    )
    base.update(overrides)
    return WorkflowDocument(**base)


async def test_create__persists_verification_parent_and_split_child(
    workflow_document_repo, tenant_orm, workflow_orm, case_orm
):
    parent = _build_document(
        tenant_orm, workflow_orm, case_orm, source=WorkflowDocumentSource.BULK
    )
    await workflow_document_repo.create(parent)

    verification = {
        "ci": {
            "value": "1234567",
            "verified_by": "staff:abc",
            "level": 1,
            "verified_at": "2026-06-10T00:00:00Z",
            "previous_value": "123456",
        }
    }
    child = _build_document(
        tenant_orm,
        workflow_orm,
        case_orm,
        source=WorkflowDocumentSource.SPLIT_CHILD,
        verification=verification,
        parent_document_id=parent.uuid,
    )

    created = await workflow_document_repo.create(child)

    expect(created.source).to(equal(WorkflowDocumentSource.SPLIT_CHILD))
    expect(created.verification).to(equal(verification))
    expect(created.parent_document_id).to(equal(parent.uuid))

    found = await workflow_document_repo.find_by_id(child.uuid, tenant_orm.uuid)
    expect(found.verification).to(equal(verification))
    expect(found.parent_document_id).to(equal(parent.uuid))


async def test_create__without_e5_fields_defaults_none(
    workflow_document_repo, tenant_orm, workflow_orm, case_orm
):
    document = _build_document(tenant_orm, workflow_orm, case_orm)

    created = await workflow_document_repo.create(document)

    expect(created.verification).to(be_none)
    expect(created.parent_document_id).to(be_none)


async def test_update__persists_verification(
    workflow_document_repo, tenant_orm, workflow_orm, case_orm
):
    document = _build_document(tenant_orm, workflow_orm, case_orm)
    created = await workflow_document_repo.create(document)

    verification = {"monto": {"value": "100.00", "verified_by": "external", "level": 0}}
    created.verification = verification
    updated = await workflow_document_repo.update(created)

    expect(updated.verification).to(equal(verification))

    found = await workflow_document_repo.find_by_id(document.uuid, tenant_orm.uuid)
    expect(found.verification).to(equal(verification))


async def test_update__keeps_parent_document_id(
    workflow_document_repo, tenant_orm, workflow_orm, case_orm
):
    parent = _build_document(tenant_orm, workflow_orm, case_orm, source=WorkflowDocumentSource.BULK)
    await workflow_document_repo.create(parent)
    child = _build_document(
        tenant_orm,
        workflow_orm,
        case_orm,
        source=WorkflowDocumentSource.SPLIT_CHILD,
        parent_document_id=parent.uuid,
    )
    created = await workflow_document_repo.create(child)

    created.extraction = {"campo": "valor"}
    updated = await workflow_document_repo.update(created)

    expect(updated.parent_document_id).to(equal(parent.uuid))
    expect(updated.source).to(equal(WorkflowDocumentSource.SPLIT_CHILD))


async def test_update__persists_needs_clarification_clear_and_field_confidence(
    workflow_document_repo, tenant_orm, workflow_orm, case_orm
):
    # C10 · el clear del flag (VerifyDocumentField) viaja por update(); antes
    # update() omitía la columna y el flag quedaba marcado para siempre en DB.
    document = _build_document(
        tenant_orm,
        workflow_orm,
        case_orm,
        needs_clarification=["ci", "monto"],
        field_confidence={"ci": 0.4, "monto": 0.9},
    )
    created = await workflow_document_repo.create(document)
    expect(created.needs_clarification).to(equal(["ci", "monto"]))
    expect(created.field_confidence).to(equal({"ci": 0.4, "monto": 0.9}))

    # Clear de "ci" tras corregir.
    created.needs_clarification = ["monto"]
    created.field_confidence = {"ci": 1.0, "monto": 0.9}
    updated = await workflow_document_repo.update(created)
    expect(updated.needs_clarification).to(equal(["monto"]))

    # El clear SOBREVIVE a un find_by_id fresco (no es solo el objeto en memoria).
    found = await workflow_document_repo.find_by_id(document.uuid, tenant_orm.uuid)
    expect(found.needs_clarification).to(equal(["monto"]))
    expect(found.field_confidence).to(equal({"ci": 1.0, "monto": 0.9}))


async def test_create__persists_needs_clarification_and_field_confidence(
    workflow_document_repo, tenant_orm, workflow_orm, case_orm
):
    document = _build_document(
        tenant_orm,
        workflow_orm,
        case_orm,
        needs_clarification=["ci"],
        field_confidence={"ci": 0.3},
    )
    created = await workflow_document_repo.create(document)

    found = await workflow_document_repo.find_by_id(document.uuid, tenant_orm.uuid)
    expect(found.needs_clarification).to(equal(["ci"]))
    expect(found.field_confidence).to(equal({"ci": 0.3}))


async def test_update__long_field_path_dedupe_does_not_overflow(
    workflow_document_repo, async_session, tenant_orm, workflow_orm, case_orm
):
    # C11 · un fieldPath >106 chars antes desbordaba el dedupe_key VARCHAR(160)
    # del case_event (500 con estado parcial). Ahora el path va hasheado, así
    # que el INSERT del evento no puede fallar por longitud. Verificamos la
    # ruta completa via VerifyDocumentField sobre repos reales (no fakes).
    from src.workflows.application.workflow_documents.verify_field import (
        FieldVerification,
        VerifyDocumentField,
    )
    from src.workflows.infrastructure.repositories.sql_case_event import (
        SQLCaseEventRepository,
    )
    from src.workflows.infrastructure.repositories.sql_human_task import (
        SQLHumanTaskRepository,
    )
    from src.workflows.infrastructure.repositories.sql_workflow_case import (
        SQLWorkflowCaseRepository,
    )

    long_path = "a" * 200  # >106; con path crudo reventaba VARCHAR(160)
    document = _build_document(
        tenant_orm,
        workflow_orm,
        case_orm,
        mapped_extraction={long_path: {"value": "old"}},
    )
    await workflow_document_repo.create(document)

    result = await VerifyDocumentField(
        tenant_id=tenant_orm.uuid,
        case_id=case_orm.uuid,
        document_id=document.uuid,
        fields=[FieldVerification(field_path=long_path, action="correct", value="new")],
        verified_by="external",
        level=0,
        case_repository=SQLWorkflowCaseRepository(session=async_session),
        document_repository=workflow_document_repo,
        case_event_repository=SQLCaseEventRepository(session=async_session),
        human_task_repository=SQLHumanTaskRepository(async_session),
        temporal_client=None,
    ).execute()

    expect(result.verified_paths).to(equal([long_path]))
    found = await workflow_document_repo.find_by_id(document.uuid, tenant_orm.uuid)
    expect(found.mapped_extraction[long_path]["value"]).to(equal("new"))


async def test_update__persists_case_reassignment(
    workflow_document_repo, async_session, tenant_orm, workflow_orm, case_orm
):
    # E5 · fan-out: CreateChildCases._reassign_document repunta el doc a su
    # child via update() — el caso DEBE viajar (bug cazado en el E2E Caso 3:
    # source cambiaba a SPLIT_CHILD pero workflow_case_id quedaba en el padre).
    from src.common.database.models.processing.workflow_case import WorkflowCaseORM

    child_case = WorkflowCaseORM(
        uuid=uuid4(),
        tenant_id=tenant_orm.uuid,
        workflow_id=workflow_orm.uuid,
        name="Child Case",
    )
    async_session.add(child_case)
    await async_session.flush()

    document = _build_document(tenant_orm, workflow_orm, case_orm)
    created = await workflow_document_repo.create(document)
    expect(created.case_id).to(equal(case_orm.uuid))

    created.case_id = child_case.uuid
    created.source = WorkflowDocumentSource.SPLIT_CHILD
    updated = await workflow_document_repo.update(created)

    expect(updated.case_id).to(equal(child_case.uuid))
    found = await workflow_document_repo.find_by_id(document.uuid, tenant_orm.uuid)
    expect(found.case_id).to(equal(child_case.uuid))
    expect(found.source).to(equal(WorkflowDocumentSource.SPLIT_CHILD))
