"""Unit tests for ``WorkflowBundleImporter`` (E6 · W4).

Covers dry-run preview and real idempotent import (2x ⇒ a NEW pipeline version,
NO duplicated doc-types). Uses lightweight in-memory fakes so version/idempotence
behaviour is observable end-to-end.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from expects import be_true, equal, expect, have_len

from src.common.domain.models.processing.document_type import (
    DocumentType,
    DocumentTypeVersion,
)
from src.common.domain.models.processing.workflow import Workflow
from src.workflows.application.workflow_rules.import_export.importer import (
    ImportConflictStrategy,
)
from src.workflows.application.workflows.import_export.importer import (
    WorkflowBundleImporter,
)
from src.workflows.domain.models.pipeline import Pipeline, PipelineVersion


# --- Fakes -------------------------------------------------------------------


class FakeWorkflowRepository:
    def __init__(self, workflow: Workflow):
        self._wf = workflow
        self.updated: list[Workflow] = []

    async def find_by_id(self, workflow_id, tenant_id):
        return self._wf if self._wf.uuid == workflow_id else None

    async def list_by_tenant(self, tenant_id, industry_id=None):
        return [self._wf]

    async def update(self, workflow):
        self._wf = workflow
        self.updated.append(workflow)
        return workflow


class FakeDocumentTypeRepository:
    def __init__(self):
        self.doc_types: dict[UUID, DocumentType] = {}
        self.versions: list[DocumentTypeVersion] = []

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
        self.pipelines: dict[str, Pipeline] = {}
        self.versions: list[PipelineVersion] = []

    async def find_by_workflow(self, workflow_id, tenant_id):
        for p in self.pipelines.values():
            if p.workflow_id == workflow_id:
                return p
        return None

    async def find_by_id(self, pipeline_id, tenant_id):
        for p in self.pipelines.values():
            if p.uuid == pipeline_id:
                return p
        return None

    async def upsert(self, pipeline):
        self.pipelines[pipeline.slug] = pipeline
        return pipeline

    async def add_version(self, version):
        self.versions.append(version)
        return version

    async def latest_version(self, pipeline_id):
        matching = [v for v in self.versions if v.pipeline_id == pipeline_id]
        return max(matching, key=lambda v: v.version) if matching else None


def _bundle() -> dict:
    return {
        "schemaVersion": "1.0",
        "kind": "workflow_bundle",
        "workflow": {"name": "Pedidos", "slug": "pedidos"},
        "documentTypes": [
            {
                "name": "Pedido",
                "slug": "pedido",
                "fields": {"type": "object", "properties": {"total": {"type": "number"}}},
                "validation_rules": [],
            }
        ],
        "pipeline": {
            "slug": "pedidos-e2e",
            "name": "Pedidos E2E",
            "kind": "ANALYSIS",
            "phases": [{"id": "ingest", "kind": "ingest", "config": {}}],
        },
        "rules": [],
        "requiresConfiguration": ["destinations", "sources"],
    }


@pytest.fixture
def workflow(tenant_id):
    return Workflow(uuid=uuid4(), tenant_id=tenant_id, name="Pedidos", slug=None, pipeline_id=None)


def _make_importer(tenant_id, workflow, wf_repo, dt_repo, pl_repo, dry_run):
    return WorkflowBundleImporter(
        workflow_id=workflow.uuid,
        tenant_id=tenant_id,
        payload=_bundle(),
        strategy=ImportConflictStrategy.OVERWRITE,
        workflow_repository=wf_repo,
        pipeline_repository=pl_repo,
        rule_repository=None,
        document_type_repository=dt_repo,
        kb_document_repository=None,
        dry_run=dry_run,
    )


async def test_import_real__binds_workflow_to_imported_pipeline(tenant_id, workflow):
    # Regresión E6: workflow.pipeline_id queda bindeado al pipeline importado (antes no).
    # Las policies viajan plegadas en config de fase (D-A): el importer solo sella las phases.
    wf_repo = FakeWorkflowRepository(workflow)
    dt_repo = FakeDocumentTypeRepository()
    pl_repo = FakePipelineRepository()
    importer = _make_importer(tenant_id, workflow, wf_repo, dt_repo, pl_repo, dry_run=False)

    report = await importer.execute()

    expect(report.pipeline_created).to(be_true)
    expect(report.pipeline_bound).to(be_true)
    pipeline = pl_repo.pipelines["pedidos-e2e"]
    # El workflow ahora apunta al pipeline del bundle (no a su default).
    expect(wf_repo._wf.pipeline_id).to(equal(pipeline.uuid))


async def test_dry_run__previews_without_writing(tenant_id, workflow):
    # Arrange
    wf_repo = FakeWorkflowRepository(workflow)
    dt_repo = FakeDocumentTypeRepository()
    pl_repo = FakePipelineRepository()
    importer = _make_importer(tenant_id, workflow, wf_repo, dt_repo, pl_repo, dry_run=True)

    # Act
    report = await importer.execute()

    # Assert — nothing persisted, but the preview reports what WOULD happen.
    expect(report.dry_run).to(be_true)
    expect(report.doc_types_created).to(equal(1))
    expect(report.pipeline_created).to(be_true)
    expect(report.pipeline_version).to(equal(1))
    expect(dt_repo.doc_types).to(have_len(0))
    expect(pl_repo.versions).to(have_len(0))
    expect(wf_repo.updated).to(have_len(0))


async def test_import_real__idempotent_new_version_no_duplicate_doctypes(tenant_id, workflow):
    # Arrange
    wf_repo = FakeWorkflowRepository(workflow)
    dt_repo = FakeDocumentTypeRepository()
    pl_repo = FakePipelineRepository()

    # Act — import twice.
    report1 = await _make_importer(tenant_id, workflow, wf_repo, dt_repo, pl_repo, dry_run=False).execute()
    report2 = await _make_importer(tenant_id, workflow, wf_repo, dt_repo, pl_repo, dry_run=False).execute()

    # Assert — first import creates the doc-type + pipeline v1 + binds workflow.
    expect(report1.doc_types_created).to(equal(1))
    expect(report1.pipeline_created).to(be_true)
    expect(report1.pipeline_version).to(equal(1))
    expect(report1.pipeline_bound).to(be_true)

    # Second import: NO new doc-type (overwrite same schema ⇒ no new dt version),
    # but a NEW pipeline version (append-only) and reuse of the container.
    expect(report2.doc_types_created).to(equal(0))
    expect(report2.doc_types_overwritten).to(equal(1))
    expect(report2.pipeline_created).to(equal(False))
    expect(report2.pipeline_version).to(equal(2))

    # Exactly one doc-type total; two pipeline versions.
    expect(dt_repo.doc_types).to(have_len(1))
    expect(pl_repo.versions).to(have_len(2))
    # Only ONE pipeline container (find-or-create by slug).
    expect(pl_repo.pipelines).to(have_len(1))
    # Workflow bound to the pipeline and slug backfilled.
    expect(wf_repo._wf.pipeline_id).to(equal(pl_repo.pipelines["pedidos-e2e"].uuid))
    expect(wf_repo._wf.slug).to(equal("pedidos"))
