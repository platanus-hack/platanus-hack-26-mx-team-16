"""Unit tests for ``WorkflowBundleExporter`` (E6 · W4).

Shape of the envelope: KB refs by slug, requiresConfiguration present, pipeline
section carries phases + policies.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from expects import be_none, contain, equal, expect, have_keys

from src.common.domain.enums.knowledge_base import KBDocumentStatus
from src.common.domain.enums.pipelines import PipelineKind, PipelineStatus
from src.common.domain.models.knowledge_base.kb_document import KBDocument
from src.common.domain.models.processing.document_type import DocumentType
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.application.workflows.import_export.exporter import (
    WorkflowBundleExporter,
)
from src.workflows.domain.models.pipeline import PhaseSpec, Pipeline, PipelineVersion


@pytest.fixture
def kb_doc(tenant_id):
    return KBDocument(
        uuid=uuid4(),
        tenant_id=tenant_id,
        file_name="Reglamento.pdf",
        slug="reglamento",
        mime="application/pdf",
        status=KBDocumentStatus.READY,
    )


@pytest.fixture
def doc_type(tenant_id, workflow_id):
    return DocumentType(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="Pedido",
        slug="pedido",
        fields={"type": "object", "properties": {"total": {"type": "number"}}},
        validation_rules=[],
        current_version=1,
    )


@pytest.fixture
def rule(tenant_id, workflow_id, kb_doc):
    return WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="Total positivo",
        slug="total_positivo",
        kind="VALIDATION",
        prompt="total > 0",
        when="@pedido.total != 0",
        config={"severity": "BLOCKER"},
        scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        knowledge_refs=[kb_doc.uuid],
        position=0,
        is_active=True,
    )


@pytest.fixture
def pipeline(tenant_id, workflow_id):
    return Pipeline(
        uuid=uuid4(),
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        slug="pedidos-e2e",
        name="Pedidos",
        kind=PipelineKind.ANALYSIS,
        status=PipelineStatus.ACTIVE,
        current_version=3,
    )


@pytest.fixture
def pipeline_version(pipeline):
    return PipelineVersion(
        uuid=uuid4(),
        pipeline_id=pipeline.uuid,
        version=3,
        phases=[PhaseSpec(id="ingest", kind="ingest"), PhaseSpec(id="deliver", kind="deliver")],
        output_schema=None,
    )


async def test_execute__envelope_shape(
    tenant_id,
    workflow_id,
    workflow_repository,
    pipeline_repository,
    workflow_rule_repository,
    document_type_repository,
    kb_document_repository,
    doc_type,
    rule,
    pipeline,
    pipeline_version,
    kb_doc,
):
    # Arrange
    workflow = Workflow(
        uuid=workflow_id,
        tenant_id=tenant_id,
        name="Pedidos Multicanal",
        slug="pedidos-multicanal",
        pipeline_id=pipeline.uuid,
    )
    workflow_repository.find_by_id.return_value = workflow
    workflow_rule_repository.list_by_workflow.return_value = [rule]
    document_type_repository.list_by_workflow.return_value = [doc_type]
    kb_document_repository.find_by_id.return_value = kb_doc
    pipeline_repository.find_by_id.return_value = pipeline
    pipeline_repository.get_version.return_value = pipeline_version

    exporter = WorkflowBundleExporter(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        workflow_repository=workflow_repository,
        pipeline_repository=pipeline_repository,
        rule_repository=workflow_rule_repository,
        document_type_repository=document_type_repository,
        kb_document_repository=kb_document_repository,
    )

    # Act
    envelope = await exporter.execute()

    # Assert
    expect(envelope).to(have_keys("schemaVersion", "workflow", "documentTypes", "rules", "pipeline"))
    expect(envelope["schemaVersion"]).to(equal("1.0"))
    expect(envelope["requiresConfiguration"]).to(contain("destinations", "sources"))
    expect(envelope["workflow"]["slug"]).to(equal("pedidos-multicanal"))
    expect(envelope["documentTypes"][0]["slug"]).to(equal("pedido"))
    # Pipeline section carries phases + policies.
    expect(envelope["pipeline"]["slug"]).to(equal("pedidos-e2e"))
    expect([p["id"] for p in envelope["pipeline"]["phases"]]).to(equal(["ingest", "deliver"]))


async def test_execute__kb_refs_by_slug(
    tenant_id,
    workflow_id,
    workflow_repository,
    pipeline_repository,
    workflow_rule_repository,
    document_type_repository,
    kb_document_repository,
    doc_type,
    rule,
    kb_doc,
):
    # Arrange — workflow with NO pipeline ⇒ pipeline section is None.
    workflow = Workflow(uuid=workflow_id, tenant_id=tenant_id, name="W", pipeline_id=None)
    workflow_repository.find_by_id.return_value = workflow
    workflow_rule_repository.list_by_workflow.return_value = [rule]
    document_type_repository.list_by_workflow.return_value = [doc_type]
    kb_document_repository.find_by_id.return_value = kb_doc

    envelope = await WorkflowBundleExporter(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        workflow_repository=workflow_repository,
        pipeline_repository=pipeline_repository,
        rule_repository=workflow_rule_repository,
        document_type_repository=document_type_repository,
        kb_document_repository=kb_document_repository,
    ).execute()

    # Assert — exported rule references KB by slug (portability fix).
    exported_rule = envelope["rules"][0]
    expect(exported_rule["knowledge_refs_external"][0]).to(have_keys("slug"))
    expect(exported_rule["knowledge_refs_external"][0]["slug"]).to(equal("reglamento"))
    expect(exported_rule["when"]).to(equal("@pedido.total != 0"))
    expect(envelope["pipeline"]).to(be_none)


async def test_execute__exports_case_noun(
    tenant_id,
    workflow_id,
    workflow_repository,
    pipeline_repository,
    workflow_rule_repository,
    document_type_repository,
    kb_document_repository,
):
    # Arrange — workflow con sustantivo del caso (case-noun §3.6).
    noun = {
        "es": {"one": "Pedido", "other": "Pedidos"},
        "en": {"one": "Order", "other": "Orders"},
    }
    workflow = Workflow(
        uuid=workflow_id, tenant_id=tenant_id, name="W", pipeline_id=None, case_noun=noun
    )
    workflow_repository.find_by_id.return_value = workflow
    workflow_rule_repository.list_by_workflow.return_value = []
    document_type_repository.list_by_workflow.return_value = []

    envelope = await WorkflowBundleExporter(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        workflow_repository=workflow_repository,
        pipeline_repository=pipeline_repository,
        rule_repository=workflow_rule_repository,
        document_type_repository=document_type_repository,
        kb_document_repository=kb_document_repository,
    ).execute()

    # Assert — el bundle transporta caseNoun (no-secreto) en camelCase.
    expect(envelope["workflow"]["caseNoun"]).to(equal(noun))
