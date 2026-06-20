"""Resolución de la receta que corre un upload (ADR 0002 · pipeline 1:1).

Cada workflow es **dueño** de su pipeline (``pipelines.workflow_id`` UNIQUE), así
que resolver es directo: el pipeline del workflow → su ``current_version``. Sin
receta utilizable (pipeline inexistente o sin ``current_version``) es un error de
configuración 409 — nunca un dispatch silencioso al vacío. Ya no hay *fallback*
por slug a una receta compartida del tenant (esas dejaron de existir).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.exceptions.processing import WorkflowPipelineNotConfiguredError
from src.workflows.domain.repositories.pipeline import PipelineRepository


@dataclass(frozen=True)
class ResolvedPipeline:
    pipeline_id: UUID
    version: int


async def resolve_workflow_pipeline(
    *,
    tenant_id: UUID,
    pipeline_repository: PipelineRepository,
    workflow_id: UUID,
) -> ResolvedPipeline:
    """La receta sellada (pipeline propio + versión activa) para un run del workflow."""
    pipeline = await pipeline_repository.find_by_workflow(workflow_id, tenant_id)
    if pipeline is None or pipeline.current_version is None:
        raise WorkflowPipelineNotConfiguredError(str(workflow_id))
    return ResolvedPipeline(pipeline_id=pipeline.uuid, version=pipeline.current_version)
