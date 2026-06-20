"""Unit tests de ``WorkflowCreator`` — copy-on-create (ADR 0002 · E7·F2).

El workflow nace **dueño de su pipeline propio**: se crea primero con
``pipeline_id=None``, luego se clona la PLANTILLA elegida en el alta
(``pipeline_template_for_slug(template_slug)`` — `workflow_type` murió en F2)
como su pipeline v1 (fases + policies) y el workflow se actualiza apuntando a
ese pipeline nuevo. Sin repo de pipelines (algunos tests) el binding queda
``NULL`` y un run da 409 más adelante.
"""

from __future__ import annotations

import pytest
from expects import be_a, be_none, equal, expect

from src.workflows.application.workflows.creator import WorkflowCreator
from src.workflows.domain.models.pipeline import Pipeline, PipelineVersion
from src.workflows.domain.recipes import pipeline_template_for_slug


@pytest.fixture(autouse=True)
def _passthrough_create(workflow_repository, pipeline_repository):
    # create/update/upsert devuelven su argumento para que la cadena
    # copy-on-create (create → upsert → add_version → update) funcione.
    workflow_repository.create.side_effect = lambda workflow: workflow
    workflow_repository.update.side_effect = lambda workflow: workflow
    pipeline_repository.upsert.side_effect = lambda pipeline: pipeline


@pytest.mark.parametrize(
    "template_slug", [None, "standard-extraction", "standard-analysis", "standard-case"]
)
async def test_execute__copies_chosen_template_into_own_pipeline(
    tenant_id, workflow_repository, pipeline_repository, template_slug
):
    # Arrange
    creator = WorkflowCreator(
        tenant_id=tenant_id,
        name="Mi workflow",
        template_slug=template_slug,
        workflow_repository=workflow_repository,
        pipeline_repository=pipeline_repository,
    )
    expected = pipeline_template_for_slug(template_slug)

    # Act
    workflow = await creator.execute()

    # Assert — el workflow se crea primero (luego se provisiona su pipeline propio).
    created = workflow_repository.create.call_args.args[0]
    expect(created.tenant_id).to(equal(tenant_id))

    # upsert recibe un Pipeline del workflow recién creado, con kind/name de la plantilla.
    pipeline_repository.upsert.assert_awaited_once()
    pipeline = pipeline_repository.upsert.call_args.args[0]
    expect(pipeline).to(be_a(Pipeline))
    expect(pipeline.workflow_id).to(equal(created.uuid))
    expect(pipeline.tenant_id).to(equal(tenant_id))
    expect(pipeline.kind).to(equal(expected.kind))
    expect(pipeline.name).to(equal(expected.name))
    expect(pipeline.current_version).to(equal(1))

    # add_version sella la v1 con las fases + policies de la plantilla.
    pipeline_repository.add_version.assert_awaited_once()
    version = pipeline_repository.add_version.call_args.args[0]
    expect(version).to(be_a(PipelineVersion))
    expect(version.pipeline_id).to(equal(pipeline.uuid))
    expect(version.version).to(equal(1))
    # Las fases (con la activación plegada en extraction_gate.config.activation y la
    # completitud en await_documents.config) se clonan tal cual de la plantilla.
    expect([phase.model_dump(exclude_none=True) for phase in version.phases]).to(
        equal(expected.phases)
    )

    # El workflow se actualiza apuntando a su pipeline nuevo y es lo que retorna.
    workflow_repository.update.assert_awaited_once()
    updated = workflow_repository.update.call_args.args[0]
    expect(updated.pipeline_id).to(equal(pipeline.uuid))
    expect(workflow.pipeline_id).to(equal(pipeline.uuid))


async def test_execute__without_pipeline_repository_leaves_binding_null(
    tenant_id, workflow_repository
):
    # Arrange — sin repo el binding queda NULL (un run resuelve/da 409 luego).
    creator = WorkflowCreator(
        tenant_id=tenant_id,
        name="Mi workflow",
        workflow_repository=workflow_repository,
    )

    # Act
    workflow = await creator.execute()

    # Assert — workflow creado con pipeline_id None y sin update posterior.
    expect(workflow.pipeline_id).to(be_none)
    workflow_repository.create.assert_awaited_once()
    expect(workflow_repository.update.await_count).to(equal(0))
