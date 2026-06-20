"""Resolución de la receta sellada/efectiva de un caso (E4 · diseño §3).

Orden: ``case.pipeline_version_id`` (sellada al arrancar el CASE#) →
``case.pipeline_id`` + current_version (elegida en POST /v1/cases) → binding
del workflow (``workflows.pipeline_id`` → resolve, con fallback
standard-extraction). Devuelve ``None`` si no hay receta utilizable — los
callers tratan eso como "sin await_documents" (comportamiento E3).
"""

from __future__ import annotations

from uuid import UUID

from src.common.domain.enums.pipelines import PhaseKind
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.domain.models.pipeline import PipelineVersion
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository


async def resolve_case_recipe(
    case: WorkflowCase,
    tenant_id: UUID,
    pipeline_repository: PipelineRepository,
    workflow_repository: WorkflowRepository | None = None,
) -> PipelineVersion | None:
    if case.pipeline_version_id is not None:
        version = await pipeline_repository.find_version_by_id(case.pipeline_version_id)
        if version is not None:
            return version

    if case.pipeline_id is not None:
        pipeline = await pipeline_repository.find_by_id(case.pipeline_id, tenant_id)
        if pipeline is not None and pipeline.current_version is not None:
            return await pipeline_repository.get_version(pipeline.uuid, pipeline.current_version)

    if workflow_repository is not None:
        workflow = await workflow_repository.find_by_id(case.workflow_id, tenant_id)
        if workflow is not None and workflow.pipeline_id is not None:
            pipeline = await pipeline_repository.find_by_id(workflow.pipeline_id, tenant_id)
            if pipeline is not None and pipeline.current_version is not None:
                return await pipeline_repository.get_version(pipeline.uuid, pipeline.current_version)
    return None


def recipe_has_await_documents(version: PipelineVersion | None) -> bool:
    if version is None:
        return False
    return any(phase.kind == PhaseKind.AWAIT_DOCUMENTS for phase in version.phases)
