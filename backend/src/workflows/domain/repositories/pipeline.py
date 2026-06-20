from abc import ABC, abstractmethod
from uuid import UUID

from src.workflows.domain.models.pipeline import Pipeline, PipelineVersion


class PipelineRepository(ABC):
    """Persistence for configurable pipelines + their immutable versions (F1)."""

    @abstractmethod
    async def find_by_id(self, pipeline_id: UUID, tenant_id: UUID) -> Pipeline | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_workflow(self, workflow_id: UUID, tenant_id: UUID) -> Pipeline | None:
        """Resolve the pipeline a workflow owns (ADR 0002 · 1:1, replaces slug lookup)."""
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, pipeline: Pipeline) -> Pipeline:
        """Create-or-update the logical container (fixtures + API)."""
        raise NotImplementedError

    @abstractmethod
    async def add_version(self, version: PipelineVersion) -> PipelineVersion:
        """Append an immutable version (append-only; (pipeline_id, version) unique)."""
        raise NotImplementedError

    @abstractmethod
    async def get_version(self, pipeline_id: UUID, version: int) -> PipelineVersion | None:
        """Load the sealed recipe a run pinned at start time."""
        raise NotImplementedError

    async def find_version_by_id(self, version_id: UUID) -> PipelineVersion | None:
        """Load a sealed version by PK (E4: ``workflow_cases.pipeline_version_id``).

        No abstracta para no romper fakes existentes; el repo SQL la implementa.
        """
        raise NotImplementedError

    @abstractmethod
    async def latest_version(self, pipeline_id: UUID) -> PipelineVersion | None:
        raise NotImplementedError

    async def list_versions(self, pipeline_id: UUID) -> list[PipelineVersion]:
        """List every sealed version of a pipeline, newest first (E6 · editor).

        No abstracta para no romper fakes existentes; el repo SQL la implementa.
        """
        raise NotImplementedError
