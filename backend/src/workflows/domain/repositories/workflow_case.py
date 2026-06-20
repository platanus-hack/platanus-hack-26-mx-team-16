from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.entities.common.pagination import Page
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.domain.filters.workflow_case import WorkflowCaseFilters


class WorkflowCaseRepository(ABC):
    @abstractmethod
    async def find_by_id(self, case_id: UUID, tenant_id: UUID) -> WorkflowCase | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_external_ref(
        self, workflow_id: UUID, external_ref: str, tenant_id: UUID
    ) -> WorkflowCase | None:
        """Find-or-create M2M (E3): el id del sistema del cliente, único por workflow."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> list[WorkflowCase]:
        raise NotImplementedError

    @abstractmethod
    async def list_children(self, parent_case_id: UUID, tenant_id: UUID) -> list[WorkflowCase]:
        """Children del fan-out (E5), orden de creación ascendente."""
        raise NotImplementedError

    @abstractmethod
    async def count_children_by_status(
        self, parent_case_id: UUID, tenant_id: UUID
    ) -> dict[str, int]:
        """``{status: n}`` de los children (E5 · panel children + auto-cierre)."""
        raise NotImplementedError

    @abstractmethod
    async def filter_paginated(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        filters: WorkflowCaseFilters,
    ) -> Page[WorkflowCase]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, case: WorkflowCase) -> WorkflowCase:
        raise NotImplementedError

    @abstractmethod
    async def update(self, case: WorkflowCase) -> WorkflowCase:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, case_id: UUID, tenant_id: UUID) -> None:
        raise NotImplementedError
