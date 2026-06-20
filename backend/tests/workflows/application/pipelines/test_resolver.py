"""Unit tests de ``resolve_workflow_pipeline`` (ADR 0002 · pipeline 1:1).

Resolución directa: el pipeline **propio** del workflow
(``find_by_workflow(workflow_id, tenant_id)``) → su ``current_version``. Sin
receta utilizable (pipeline inexistente o sin ``current_version``) es un 409
(``WorkflowPipelineNotConfiguredError``). Ya no hay binding por
``workflow_pipeline_id`` ni *fallback* por slug a la receta ``standard-extraction``.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.enums.pipelines import PipelineKind
from src.common.domain.exceptions.processing import WorkflowPipelineNotConfiguredError
from src.workflows.application.pipelines.resolver import resolve_workflow_pipeline
from src.workflows.domain.models.pipeline import Pipeline


def _pipeline(tenant_id, workflow_id, *, slug="wf-pipeline", current_version=1) -> Pipeline:
    return Pipeline(
        uuid=uuid4(),
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        slug=slug,
        name="Receta",
        kind=PipelineKind.EXTRACTION,
        current_version=current_version,
    )


async def test_resolve__seals_workflow_pipeline_and_current_version(tenant_id, pipeline_repository):
    # Arrange
    workflow_id = uuid4()
    owned = _pipeline(tenant_id, workflow_id, current_version=7)
    pipeline_repository.find_by_workflow.return_value = owned

    # Act
    resolved = await resolve_workflow_pipeline(
        tenant_id=tenant_id,
        pipeline_repository=pipeline_repository,
        workflow_id=workflow_id,
    )

    # Assert — sella el pipeline propio del workflow + su versión activa
    expect(resolved.pipeline_id).to(equal(owned.uuid))
    expect(resolved.version).to(equal(7))
    pipeline_repository.find_by_workflow.assert_awaited_once_with(workflow_id, tenant_id)


async def test_resolve__no_pipeline_for_workflow_raises_409(tenant_id, pipeline_repository):
    # Arrange — el workflow aún no tiene pipeline configurado
    pipeline_repository.find_by_workflow.return_value = None

    # Act / Assert
    with pytest.raises(WorkflowPipelineNotConfiguredError) as exc_info:
        await resolve_workflow_pipeline(
            tenant_id=tenant_id,
            pipeline_repository=pipeline_repository,
            workflow_id=uuid4(),
        )

    expect(exc_info.value.status_code).to(equal(409))


async def test_resolve__pipeline_without_current_version_raises_409(tenant_id, pipeline_repository):
    # Arrange — existe el contenedor pero nunca se publicó una versión
    workflow_id = uuid4()
    pipeline_repository.find_by_workflow.return_value = _pipeline(
        tenant_id, workflow_id, current_version=None
    )

    # Act / Assert
    with pytest.raises(WorkflowPipelineNotConfiguredError) as exc_info:
        await resolve_workflow_pipeline(
            tenant_id=tenant_id,
            pipeline_repository=pipeline_repository,
            workflow_id=workflow_id,
        )

    expect(exc_info.value.status_code).to(equal(409))
