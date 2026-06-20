"""Builders E5 (W1): los campos nuevos de la cadena de datos viajan ORM → dominio."""

from datetime import datetime, timezone
from uuid import uuid4

from expects import be_none, equal, expect

from src.common.database.models.human_task import HumanTaskORM
from src.common.database.models.processing.workflow_case import WorkflowCaseORM
from src.common.database.models.processing.workflow_rule import WorkflowRuleORM
from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.common.domain.enums.workflows import WorkflowDocumentSource
from src.workflows.infrastructure.builders.human_task import build_human_task
from src.workflows.infrastructure.builders.workflow_case import build_workflow_case
from src.workflows.infrastructure.builders.workflow_document import build_workflow_document
from src.workflows.infrastructure.builders.workflow_rule import build_workflow_rule


def test_build_workflow_case__maps_parent_case_id():
    parent_id = uuid4()
    orm = WorkflowCaseORM(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="Child 001",
        status="PROCESSING",
        parent_case_id=parent_id,
    )

    case = build_workflow_case(orm)

    expect(case.parent_case_id).to(equal(parent_id))


def test_build_workflow_case__parent_case_id_defaults_to_none():
    orm = WorkflowCaseORM(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="Case",
        status="RECEIVING",
    )

    case = build_workflow_case(orm)

    expect(case.parent_case_id).to(be_none)


def test_workflow_case_persist_dict__includes_parent_case_id():
    parent_id = uuid4()
    orm = WorkflowCaseORM(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="Child 002",
        status="PROCESSING",
        parent_case_id=parent_id,
    )

    case = build_workflow_case(orm)

    expect(case.persist_dict["parent_case_id"]).to(equal(parent_id))


def test_build_workflow_document__maps_verification_parent_and_split_child():
    parent_doc_id = uuid4()
    verification = {
        "monto": {
            "value": "100.00",
            "verified_by": "staff:abc",
            "level": 1,
            "verified_at": "2026-06-10T00:00:00Z",
            "previous_value": "10000",
        }
    }
    orm = WorkflowDocumentORM(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="persona_001.pdf",
        status="EXTRACTED",
        source="SPLIT_CHILD",
        extraction={},
        validation=[],
        extraction_metadata={},
        verification=verification,
        parent_document_id=parent_doc_id,
    )

    doc = build_workflow_document(orm)

    expect(doc.source).to(equal(WorkflowDocumentSource.SPLIT_CHILD))
    expect(doc.verification).to(equal(verification))
    expect(doc.parent_document_id).to(equal(parent_doc_id))


def test_workflow_document_persist_dict__includes_verification_and_parent():
    parent_doc_id = uuid4()
    verification = {"ci": {"value": "1234567", "verified_by": "external", "level": 0}}
    orm = WorkflowDocumentORM(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="doc.pdf",
        status="EXTRACTED",
        source="SINGLE",
        extraction={},
        validation=[],
        extraction_metadata={},
        verification=verification,
        parent_document_id=parent_doc_id,
    )

    doc = build_workflow_document(orm)

    expect(doc.persist_dict["verification"]).to(equal(verification))
    expect(doc.persist_dict["parent_document_id"]).to(equal(parent_doc_id))


def test_build_human_task__maps_stage_and_claim():
    claimed_at = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
    claimed_by = f"staff:{uuid4()}"
    orm = HumanTaskORM(
        uuid=uuid4(),
        tenant_id=uuid4(),
        task_key="CASE#abc:approval:review_l1",
        kind="approval",
        status="pending",
        assignee_mode="internal_queue",
        payload={},
        stage="review_l1",
        claimed_by=claimed_by,
        claimed_at=claimed_at,
    )

    task = build_human_task(orm)

    expect(task.stage).to(equal("review_l1"))
    expect(task.claimed_by).to(equal(claimed_by))
    expect(task.claimed_at).to(equal(claimed_at))


def test_build_human_task__stage_and_claim_default_to_none():
    orm = HumanTaskORM(
        uuid=uuid4(),
        tenant_id=uuid4(),
        task_key="CASE#abc:approval",
        kind="approval",
        status="pending",
        assignee_mode="internal_queue",
        payload={},
    )

    task = build_human_task(orm)

    expect(task.stage).to(be_none)
    expect(task.claimed_by).to(be_none)
    expect(task.claimed_at).to(be_none)


def test_build_workflow_rule__maps_when_from_when_expr():
    orm = WorkflowRuleORM(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="CI válida",
        slug="ci-valido",
        position=0,
        is_active=True,
        kind="CHECKSUM",
        prompt="La CI debe ser válida",
        config={},
        scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        knowledge_refs=[],
        when_expr='@persona.tipo_entidad == "natural"',
    )

    rule = build_workflow_rule(orm)

    expect(rule.when).to(equal('@persona.tipo_entidad == "natural"'))


def test_build_workflow_rule__when_defaults_to_none():
    orm = WorkflowRuleORM(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name="Monto positivo",
        slug="monto-positivo",
        position=0,
        is_active=True,
        kind="GENERIC",
        prompt="El monto debe ser mayor a 0",
        config={},
        scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        knowledge_refs=[],
    )

    rule = build_workflow_rule(orm)

    expect(rule.when).to(be_none)
