"""SQLPipelineRepository.list_versions — historial de versiones (E6 · editor).

Newest-first; vacío si el pipeline no tiene versiones. Espeja el estilo de los
demás tests de repos SQL (DB real vía conftest ``async_session``).

ADR 0002: ``pipelines.workflow_id`` es FK NOT NULL + UNIQUE → cada pipeline que
insertamos necesita su PROPIA fila ``workflows`` (distinta por la UNIQUE).
"""

from __future__ import annotations

from uuid import uuid4

from expects import be_empty, equal, expect

from src.common.database.models.workspace import WorkflowORM
from src.common.domain.enums.pipelines import PipelineKind, PipelineStatus
from src.workflows.domain.models.pipeline import Pipeline, PipelineVersion
from src.workflows.infrastructure.repositories.sql_pipeline import SQLPipelineRepository


async def _make_workflow(async_session, tenant_id):
    """Insert a real ``workflows`` row to satisfy the pipeline FK (one per pipeline)."""
    workflow = WorkflowORM(
        uuid=uuid4(),
        tenant_id=tenant_id,
        name="Test Workflow",
    )
    async_session.add(workflow)
    await async_session.flush()
    return workflow


def _pipeline(tenant_id, workflow_id) -> Pipeline:
    return Pipeline(
        uuid=uuid4(),
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        slug=f"pl-{uuid4().hex[:8]}",
        name="Test Pipeline",
        kind=PipelineKind.EXTRACTION,
        status=PipelineStatus.ACTIVE,
        current_version=1,
    )


def _version(pipeline_id, version: int) -> PipelineVersion:
    return PipelineVersion(
        uuid=uuid4(),
        pipeline_id=pipeline_id,
        version=version,
        phases=[{"id": "ingest", "kind": "ingest", "config": {}}],
        output_schema=None,
    )


async def test_list_versions__empty_when_no_versions(async_session, tenant_orm):
    repo = SQLPipelineRepository(session=async_session)
    workflow = await _make_workflow(async_session, tenant_orm.uuid)
    pipeline = await repo.upsert(_pipeline(tenant_orm.uuid, workflow.uuid))

    expect(await repo.list_versions(pipeline.uuid)).to(be_empty)


async def test_list_versions__returns_all_newest_first(async_session, tenant_orm):
    repo = SQLPipelineRepository(session=async_session)
    workflow = await _make_workflow(async_session, tenant_orm.uuid)
    pipeline = await repo.upsert(_pipeline(tenant_orm.uuid, workflow.uuid))
    await repo.add_version(_version(pipeline.uuid, 1))
    await repo.add_version(_version(pipeline.uuid, 2))
    await repo.add_version(_version(pipeline.uuid, 3))

    versions = await repo.list_versions(pipeline.uuid)

    expect([v.version for v in versions]).to(equal([3, 2, 1]))
    expect(versions[0].created_at is not None).to(equal(True))


async def test_list_versions__scoped_to_pipeline(async_session, tenant_orm):
    repo = SQLPipelineRepository(session=async_session)
    # Distinct workflow per pipeline — UNIQUE(workflow_id) (ADR 0002).
    workflow_a = await _make_workflow(async_session, tenant_orm.uuid)
    workflow_b = await _make_workflow(async_session, tenant_orm.uuid)
    pipeline_a = await repo.upsert(_pipeline(tenant_orm.uuid, workflow_a.uuid))
    pipeline_b = await repo.upsert(_pipeline(tenant_orm.uuid, workflow_b.uuid))
    await repo.add_version(_version(pipeline_a.uuid, 1))
    await repo.add_version(_version(pipeline_b.uuid, 1))
    await repo.add_version(_version(pipeline_b.uuid, 2))

    expect([v.version for v in await repo.list_versions(pipeline_a.uuid)]).to(equal([1]))
    expect([v.version for v in await repo.list_versions(pipeline_b.uuid)]).to(equal([2, 1]))
