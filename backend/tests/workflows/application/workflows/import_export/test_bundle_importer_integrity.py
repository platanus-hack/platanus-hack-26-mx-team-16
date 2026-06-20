"""Regression tests for bundle import integrity (E6 · W4 · ADR 0002).

Two confirmed bugs guarded here:

BUG 3 (pipeline ownership): ADR 0002 makes every pipeline owned 1:1 by its
workflow, so the import ALWAYS appends an immutable version to the workflow's
OWN pipeline (resolved via ``find_by_workflow``) and advances its
``current_version`` on success — never touching any sibling's pipeline.

BUG 5 (non-atomic import): an import where a rule fails to resolve MUST leave
the original rules intact and MUST NOT advance the workflow's own pipeline to
the half-applied recipe (the appended version stays inert / ``current_version``
unchanged).
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from expects import equal, expect, have_len

from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.application.workflow_rules.import_export.importer import (
    ImportConflictStrategy,
)
from src.workflows.application.workflows.import_export.importer import (
    WorkflowBundleImporter,
)
from src.workflows.domain.models.pipeline import Pipeline, PipelineVersion
from src.workflows.domain.recipes import standard_extraction_phases
from src.workflows.infrastructure.services.rules import registry
from src.workflows.infrastructure.services.rules.bootstrap import register_stub_kinds


# --- Fakes -------------------------------------------------------------------


class FakeWorkflowRepository:
    """Multi-workflow tenant repo so sibling sharing is observable."""

    def __init__(self, workflows: list[Workflow]):
        self._by_id: dict[UUID, Workflow] = {w.uuid: w for w in workflows}
        self.updated: list[Workflow] = []

    async def find_by_id(self, workflow_id, tenant_id):
        return self._by_id.get(workflow_id)

    async def list_by_tenant(self, tenant_id, industry_id=None):
        return list(self._by_id.values())

    async def update(self, workflow):
        self._by_id[workflow.uuid] = workflow
        self.updated.append(workflow)
        return workflow


class FakeDocumentTypeRepository:
    def __init__(self):
        self.doc_types: dict[UUID, object] = {}
        self.versions: list = []

    async def list_by_workflow(self, workflow_id, tenant_id):
        return [dt for dt in self.doc_types.values() if dt.workflow_id == workflow_id]

    async def create(self, document_type):
        self.doc_types[document_type.uuid] = document_type
        return document_type

    async def update(self, document_type):
        self.doc_types[document_type.uuid] = document_type
        return document_type

    async def add_version(self, version):
        self.versions.append(version)
        return version

    async def latest_version(self, document_type_id):
        matching = [v for v in self.versions if v.document_type_id == document_type_id]
        return max(matching, key=lambda v: v.version) if matching else None


class FakePipelineRepository:
    def __init__(self):
        self.pipelines: dict[UUID, Pipeline] = {}
        self.versions: list[PipelineVersion] = []

    def seed(self, pipeline: Pipeline) -> None:
        self.pipelines[pipeline.uuid] = pipeline

    async def find_by_workflow(self, workflow_id, tenant_id):
        for p in self.pipelines.values():
            if p.workflow_id == workflow_id:
                return p
        return None

    async def find_by_id(self, pipeline_id, tenant_id):
        return self.pipelines.get(pipeline_id)

    async def upsert(self, pipeline):
        self.pipelines[pipeline.uuid] = pipeline
        return pipeline

    async def add_version(self, version):
        self.versions.append(version)
        return version

    async def latest_version(self, pipeline_id):
        matching = [v for v in self.versions if v.pipeline_id == pipeline_id]
        return max(matching, key=lambda v: v.version) if matching else None


class FakeWorkflowRuleRepository:
    def __init__(self, rules: list[WorkflowRule] | None = None):
        self.rules: dict[UUID, WorkflowRule] = {r.uuid: r for r in (rules or [])}

    async def list_by_workflow(self, workflow_id, tenant_id):
        return [r for r in self.rules.values() if r.workflow_id == workflow_id]

    async def create(self, rule):
        self.rules[rule.uuid] = rule
        return rule

    async def delete(self, rule_id, tenant_id):
        self.rules.pop(rule_id, None)


# --- Fixtures ----------------------------------------------------------------


@pytest.fixture
def target_workflow(tenant_id):
    return Workflow(uuid=uuid4(), tenant_id=tenant_id, name="Pedidos", slug="pedidos", pipeline_id=None)


@pytest.fixture(autouse=True)
def _isolated_registry():
    registry.clear()
    register_stub_kinds()
    yield
    registry.clear()


def _bundle() -> dict:
    """A bundle for a workflow that already owns its private pipeline (ADR 0002)."""
    return {
        "schemaVersion": "1.0",
        "kind": "workflow_bundle",
        "workflow": {"name": "Pedidos", "slug": "pedidos"},
        "documentTypes": [],
        "pipeline": {
            "slug": "pedidos-custom",
            "name": "Pedidos custom",
            "kind": "ANALYSIS",
            "phases": [{"id": "ingest", "kind": "ingest", "config": {}}],
        },
        "rules": [],
    }


# --- BUG 3 -------------------------------------------------------------------


async def test_import__appends_version_to_workflow_own_pipeline_and_leaves_sibling_untouched(
    tenant_id, target_workflow
):
    # Arrange — ADR 0002: the target workflow owns its OWN pipeline (copy-on-create)
    # at current_version=1, plus an UNRELATED sibling with its own pipeline. The
    # import must append to the target's pipeline only, never the sibling's.
    own = Pipeline(
        uuid=uuid4(),
        workflow_id=target_workflow.uuid,
        tenant_id=tenant_id,
        slug="pedidos-pipeline",
        name="Pedidos",
        kind="ANALYSIS",
        current_version=1,
    )
    target_workflow.pipeline_id = own.uuid
    pl_repo = FakePipelineRepository()
    pl_repo.seed(own)
    own_v1 = PipelineVersion(
        uuid=uuid4(),
        pipeline_id=own.uuid,
        version=1,
        phases=standard_extraction_phases(),
        output_schema=None,
    )
    pl_repo.versions.append(own_v1)

    sibling_pipeline = Pipeline(
        uuid=uuid4(),
        workflow_id=uuid4(),
        tenant_id=tenant_id,
        slug="otro-pipeline",
        name="Otro",
        kind="EXTRACTION",
        current_version=1,
    )
    pl_repo.seed(sibling_pipeline)
    sibling = Workflow(
        uuid=sibling_pipeline.workflow_id,
        tenant_id=tenant_id,
        name="Otro",
        slug="otro",
        pipeline_id=sibling_pipeline.uuid,
    )
    wf_repo = FakeWorkflowRepository([target_workflow, sibling])

    importer = WorkflowBundleImporter(
        workflow_id=target_workflow.uuid,
        tenant_id=tenant_id,
        payload=_bundle(),
        strategy=ImportConflictStrategy.OVERWRITE,
        workflow_repository=wf_repo,
        pipeline_repository=pl_repo,
        rule_repository=FakeWorkflowRuleRepository(),
        document_type_repository=FakeDocumentTypeRepository(),
        kb_document_repository=None,
        dry_run=False,
    )

    # Act
    report = await importer.execute()

    # Assert — the import appended a NEW version to the workflow's OWN pipeline and
    # advanced its active pointer (no shared/canonical detection, no re-scoping).
    expect(report.pipeline_created).to(equal(False))
    expect(report.pipeline_bound).to(equal(True))
    own_versions = [v for v in pl_repo.versions if v.pipeline_id == own.uuid]
    expect(own_versions).to(have_len(2))
    expect(report.pipeline_version).to(equal(2))
    expect(own.current_version).to(equal(2))
    # The workflow still points at its same (own) pipeline.
    expect(wf_repo._by_id[target_workflow.uuid].pipeline_id).to(equal(own.uuid))

    # The unrelated sibling's pipeline is untouched: still v1, no new version.
    expect(sibling_pipeline.current_version).to(equal(1))
    sibling_versions = [v for v in pl_repo.versions if v.pipeline_id == sibling_pipeline.uuid]
    expect(sibling_versions).to(have_len(0))
    expect(sibling.pipeline_id).to(equal(sibling_pipeline.uuid))


# --- BUG 5 -------------------------------------------------------------------


def _failing_rules_bundle() -> dict:
    """A private pipeline plus a rule whose scope references an unresolvable
    doc-type slug (raises InvalidWorkflowRuleConfigError ⇒ rules_failed)."""
    return {
        "schemaVersion": "1.0",
        "kind": "workflow_bundle",
        "workflow": {"name": "Pedidos", "slug": "pedidos"},
        "documentTypes": [],
        "pipeline": {
            "slug": "pedidos-private",  # private to the target — would normally rebind
            "name": "Pedidos private",
            "kind": "ANALYSIS",
            "phases": [{"id": "ingest", "kind": "ingest", "config": {}}],
        },
        "rules": [
            {
                "name": "Regla rota",
                "slug": "regla_rota",
                "kind": "VALIDATION",
                "prompt": "check",
                "scope": {"document_type_slug": "does-not-exist"},
            }
        ],
    }


async def test_failing_rule__leaves_originals_intact_and_does_not_rebind_workflow(
    tenant_id, target_workflow
):
    # Arrange — workflow already owns its original pipeline; an existing rule that
    # must survive an OVERWRITE whose replacement fails to resolve.
    original_pipeline = Pipeline(
        uuid=uuid4(),
        workflow_id=target_workflow.uuid,
        tenant_id=tenant_id,
        slug="pedidos-orig",
        name="Pedidos orig",
        kind="ANALYSIS",
        current_version=1,
    )
    target_workflow.pipeline_id = original_pipeline.uuid
    pl_repo = FakePipelineRepository()
    pl_repo.seed(original_pipeline)

    existing_rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=target_workflow.uuid,
        name="Regla rota",
        slug="regla_rota",
        kind="VALIDATION",
        prompt="original",
    )
    rule_repo = FakeWorkflowRuleRepository([existing_rule])
    wf_repo = FakeWorkflowRepository([target_workflow])

    importer = WorkflowBundleImporter(
        workflow_id=target_workflow.uuid,
        tenant_id=tenant_id,
        payload=_failing_rules_bundle(),
        strategy=ImportConflictStrategy.OVERWRITE,
        workflow_repository=wf_repo,
        pipeline_repository=pl_repo,
        rule_repository=rule_repo,
        document_type_repository=FakeDocumentTypeRepository(),
        kb_document_repository=None,
        dry_run=False,
    )

    # Act
    report = await importer.execute()

    # Assert — the rule failed to resolve…
    expect(report.rules_failed).to(equal(1))
    # …so the original rule is still present and unchanged (no delete-then-lose).
    surviving = await rule_repo.list_by_workflow(target_workflow.uuid, tenant_id)
    expect(surviving).to(have_len(1))
    expect(surviving[0].uuid).to(equal(existing_rule.uuid))
    expect(surviving[0].prompt).to(equal("original"))

    # …and the workflow still points at its original pipeline (no rebind).
    expect(wf_repo._by_id[target_workflow.uuid].pipeline_id).to(equal(original_pipeline.uuid))
    expect(report.pipeline_bound).to(equal(False))
    # The workflow's own pipeline got a new (inert) version appended, but its active
    # recipe pointer is untouched — the half-applied recipe is NOT activated.
    own_versions = [v for v in pl_repo.versions if v.pipeline_id == original_pipeline.uuid]
    expect(own_versions).to(have_len(1))
    expect(original_pipeline.current_version).to(equal(1))
