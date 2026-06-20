"""Tests for ``WorkflowDocumentTypesImporter`` (E6 · W4).

Find-or-create by slug: SKIP leaves existing untouched, OVERWRITE rewrites and
seals a new version only when the schema differs.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from expects import equal, expect, have_len

from src.common.domain.models.processing.document_type import (
    DocumentType,
    DocumentTypeVersion,
)
from src.workflows.application.document_types.import_export.importer import (
    WorkflowDocumentTypesImporter,
)
from src.workflows.application.workflow_rules.import_export.importer import (
    ImportConflictStrategy,
)


class FakeDocumentTypeRepository:
    def __init__(self, existing=None):
        self.doc_types: dict[UUID, DocumentType] = {dt.uuid: dt for dt in (existing or [])}
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


@pytest.fixture
def workflow_id():
    return uuid4()


def _payload(fields=None):
    return [
        {
            "name": "Pedido",
            "slug": "pedido",
            "fields": fields or {"type": "object", "properties": {"total": {"type": "number"}}},
            "validation_rules": [],
        }
    ]


async def test_create__new_doctype_with_sealed_v1(tenant_id, workflow_id):
    # Arrange
    repo = FakeDocumentTypeRepository()
    importer = WorkflowDocumentTypesImporter(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        payload=_payload(),
        strategy=ImportConflictStrategy.SKIP,
        document_type_repository=repo,
    )

    # Act
    report = await importer.execute()

    # Assert
    expect(report.created).to(equal(1))
    expect(repo.doc_types).to(have_len(1))
    expect(repo.versions).to(have_len(1))
    expect(report.slug_map["pedido"]).to(equal("pedido"))


async def test_skip__leaves_existing_untouched(tenant_id, workflow_id):
    # Arrange — existing doc-type with the same slug.
    existing = DocumentType(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="Pedido",
        slug="pedido",
        fields={"type": "object", "properties": {"x": {"type": "string"}}},
        current_version=1,
    )
    repo = FakeDocumentTypeRepository(existing=[existing])

    # Act
    report = await WorkflowDocumentTypesImporter(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        payload=_payload(),
        strategy=ImportConflictStrategy.SKIP,
        document_type_repository=repo,
    ).execute()

    # Assert — skipped, no new doc-type, no new version.
    expect(report.skipped).to(equal(1))
    expect(report.created).to(equal(0))
    expect(repo.doc_types).to(have_len(1))
    expect(repo.versions).to(have_len(0))


async def test_overwrite__seals_new_version_when_schema_differs(tenant_id, workflow_id):
    # Arrange
    existing = DocumentType(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="Pedido",
        slug="pedido",
        fields={"type": "object", "properties": {"x": {"type": "string"}}},
        current_version=1,
    )
    repo = FakeDocumentTypeRepository(existing=[existing])

    # Act
    report = await WorkflowDocumentTypesImporter(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        payload=_payload(),  # different fields
        strategy=ImportConflictStrategy.OVERWRITE,
        document_type_repository=repo,
    ).execute()

    # Assert — overwritten, new sealed version, still a single doc-type.
    expect(report.overwritten).to(equal(1))
    expect(repo.doc_types).to(have_len(1))
    expect(repo.versions).to(have_len(1))
    expect(repo.versions[0].version).to(equal(2))
    expect(repo.doc_types[existing.uuid].current_version).to(equal(2))
