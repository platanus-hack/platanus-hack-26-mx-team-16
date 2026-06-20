"""Use case: compose the Overview tab payload.

The repository exposes three independent reads (`get_overview_summary`,
`get_throughput`, `get_recent_documents`); this use case fans them out
in parallel with `asyncio.gather` so the endpoint latency is `max(t1,
t2, t3)` rather than the sum.

`now` is taken once at execute-time and threaded through the three repo
calls so every sub-result agrees on the same wall-clock — important
when sub-queries depend on month/day boundaries.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.dashboard.domain.entities.overview import OverviewData
from src.dashboard.domain.repositories.dashboard_metrics import (
    DashboardMetricsRepository,
)


@dataclass
class GetOverview(UseCase):
    tenant_id: UUID
    tenant_time_zone: str
    throughput_months: int
    recent_limit: int
    dashboard_metrics_repository: DashboardMetricsRepository

    async def execute(self) -> OverviewData:
        now = datetime.now(UTC)
        summary, throughput, recent_documents = await asyncio.gather(
            self.dashboard_metrics_repository.get_overview_summary(
                tenant_id=self.tenant_id,
                now=now,
                time_zone=self.tenant_time_zone,
            ),
            self.dashboard_metrics_repository.get_throughput(
                tenant_id=self.tenant_id,
                months=self.throughput_months,
                now=now,
            ),
            self.dashboard_metrics_repository.get_recent_documents(
                tenant_id=self.tenant_id,
                limit=self.recent_limit,
            ),
        )
        return OverviewData(
            summary=summary,
            throughput=throughput,
            recent_documents=recent_documents,
        )
