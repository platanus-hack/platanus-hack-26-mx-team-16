"""Repository interface for dashboard aggregated metrics.

The interface is intentionally split into one method per sub-section so
the use cases can run them concurrently with `asyncio.gather(...)` —
turning a 3x serial query into a single round-trip's worth of latency.

All methods are tenant-scoped. The `now` parameter is always provided
by the caller (use case) so that tests can pin time and the same value
is used across the methods that compose a single response (consistency).
"""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.dashboard.domain.entities.overview import (
    OverviewSummary,
    RecentDocument,
    ThroughputBucket,
)
from src.dashboard.domain.entities.processing import (
    LiveProcessingDocument,
    PipelineStage,
    ProcessingSummary,
)


class DashboardMetricsRepository(ABC):
    @abstractmethod
    async def get_overview_summary(
        self,
        *,
        tenant_id: UUID,
        now: datetime,
        time_zone: str,
    ) -> OverviewSummary:
        raise NotImplementedError

    @abstractmethod
    async def get_throughput(
        self,
        *,
        tenant_id: UUID,
        months: int,
        now: datetime,
    ) -> list[ThroughputBucket]:
        raise NotImplementedError

    @abstractmethod
    async def get_recent_documents(
        self,
        *,
        tenant_id: UUID,
        limit: int,
    ) -> list[RecentDocument]:
        raise NotImplementedError

    @abstractmethod
    async def get_processing_summary(
        self,
        *,
        tenant_id: UUID,
        now: datetime,
        time_zone: str,
    ) -> ProcessingSummary:
        raise NotImplementedError

    @abstractmethod
    async def list_pipeline_stages(
        self,
        *,
        tenant_id: UUID,
    ) -> list[PipelineStage]:
        raise NotImplementedError

    @abstractmethod
    async def list_live_processing(
        self,
        *,
        tenant_id: UUID,
        limit: int,
        avg_processing_seconds: float | None,
        now: datetime,
    ) -> list[LiveProcessingDocument]:
        raise NotImplementedError
