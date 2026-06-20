from abc import ABC, abstractmethod
from uuid import UUID

from src.common.domain.entities.common.pagination import Page
from src.common.domain.enums.workflows import WorkflowProcessingJobTrigger
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.domain.filters.workflow_processing_job import WorkflowProcessingJobFilters


class WorkflowProcessingJobRepository(ABC):
    @abstractmethod
    async def create(self, processing_job: WorkflowProcessingJob) -> WorkflowProcessingJob:
        raise NotImplementedError

    @abstractmethod
    async def filter_paginated(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        filters: WorkflowProcessingJobFilters,
    ) -> Page[WorkflowProcessingJob]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_uuid(self, uuid: UUID) -> WorkflowProcessingJob | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_temporal_workflow_id(self, temporal_workflow_id: str) -> WorkflowProcessingJob | None:
        raise NotImplementedError

    @abstractmethod
    async def claim(self, uuid: UUID) -> WorkflowProcessingJob | None:
        """Marca el set como `running` con SELECT … FOR UPDATE SKIP LOCKED.
        Devuelve None si otro worker ya lo agarró."""
        raise NotImplementedError

    @abstractmethod
    async def mark_done(self, uuid: UUID, summary: dict | None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def mark_failed(self, uuid: UUID, error: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def reset_to_pending(
        self,
        uuid: UUID,
        trigger: WorkflowProcessingJobTrigger | None = None,
    ) -> None:
        """Llevar un set de `failed` (o cualquier estado) de vuelta a `pending`,
        limpiando `error` y `started_at`/`finished_at` y dejando `attempts`
        para auditoría. Usado en re-extract. Si se pasa ``trigger``, también
        actualiza la columna para reflejar el origen del nuevo dispatch."""
        raise NotImplementedError

    @abstractmethod
    async def list_unfinished(self) -> list[WorkflowProcessingJob]:
        """Para el recovery on-startup. Filtra status IN ('pending', 'running')."""
        raise NotImplementedError

    @abstractmethod
    async def list_by_workflow(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        workflow_case_id: UUID | None = None,
    ) -> list[WorkflowProcessingJob]:
        raise NotImplementedError

    @abstractmethod
    async def list_for_replay(
        self,
        workflow_id: UUID,
        tenant_id: UUID,
        since_seq: int = 0,
        workflow_case_id: UUID | None = None,
    ) -> list[WorkflowProcessingJob]:
        """Sets que el SSE debe re-emitir: filtra por workflow + tenant
        (+ workflow_case_id opcional) y `last_seq > since_seq`. Devuelve sólo
        las filas cuya secuencia avanzó respecto al cursor del cliente."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, uuid: UUID, tenant_id: UUID) -> None:
        """Borra el set (los WorkflowDocument hijos quedan con
        processing_job_id=NULL via la FK ON DELETE SET NULL)."""
        raise NotImplementedError

    async def failed_case_ids(self, case_ids: list[UUID], tenant_id: UUID) -> set[UUID]:
        """Subconjunto de ``case_ids`` con al menos un run FAILED (badge
        «Procesamiento fallido» de la lista de casos).

        No abstracta para no romper fakes existentes; el repo SQL la implementa.
        """
        raise NotImplementedError

    async def list_by_source_token(
        self,
        route_token: str,
        tenant_id: UUID,
        *,
        limit: int = 200,
    ) -> list[WorkflowProcessingJob]:
        """Sets abiertos por un Source de ingesta (id ``SRC#{route_token}_FILE#…``),
        más recientes primero, enriquecidos con ``file_name``. Sustenta la pestaña
        «Eventos» del detalle del source.

        No abstracta para no romper fakes existentes; el repo SQL la implementa.
        """
        raise NotImplementedError
