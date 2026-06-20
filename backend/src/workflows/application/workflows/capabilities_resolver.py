"""Resuelve las capacidades de un workflow desde su pipeline vigente (E7 · F0).

El servicio de dominio ``derive_capabilities`` es puro (no toca repos); esta capa
de aplicación se encarga del I/O: del workflow → su pipeline (1:1, ADR 0002) → la
versión ``current_version`` → ``derive_capabilities``. El presenter expone el
resultado para que el FE gatee tabs/acciones sin mirar ``workflow_type``.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.models.processing.workflow import Workflow
from src.workflows.domain.models.pipeline import PipelineVersion
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.services.capabilities import Capability, derive_capabilities


@dataclass
class WorkflowCapabilitiesResolver:
    pipeline_repository: PipelineRepository

    async def for_workflow(self, workflow: Workflow) -> set[Capability]:
        version = await self._current_version(workflow.uuid, workflow.tenant_id)
        return derive_capabilities(version)

    async def for_workflows(self, workflows: list[Workflow]) -> dict[UUID, set[Capability]]:
        # N+1 sobre la lista (2 lecturas por workflow). Aceptable a escala de un
        # tenant; si crece, un método batch en el repo lo colapsa a una query.
        return {workflow.uuid: await self.for_workflow(workflow) for workflow in workflows}

    async def _current_version(self, workflow_id: UUID, tenant_id: UUID) -> PipelineVersion | None:
        pipeline = await self.pipeline_repository.find_by_workflow(workflow_id, tenant_id)
        if pipeline is None or pipeline.current_version is None:
            return None
        return await self.pipeline_repository.get_version(pipeline.uuid, pipeline.current_version)


def capabilities_to_payload(capabilities: set[Capability]) -> list[str]:
    """Orden estable (los sets no lo tienen) para un contrato/diff determinista."""
    return sorted(capability.value for capability in capabilities)
