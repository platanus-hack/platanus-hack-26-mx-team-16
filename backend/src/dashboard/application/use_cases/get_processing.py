"""Use case: compose the Processing tab payload.

Like `GetOverview`, this fans out the independent repo reads in
parallel. `list_live_processing` depends on `summary.avg_processing_seconds`
for its ETA calculation — but rather than serialising the calls, we let
both queries run and pass `avg_processing_seconds=None` to live_processing
on this same call: the SQL repo already handles None gracefully (no ETA),
and the resulting eta_seconds=None matches the empty-data semantics.

For a tenant with completed documents, the next refresh (push-triggered
by SSE) will produce ETAs from the freshly computed average — within ~5s
of the first completion. Trading absolute first-render ETA accuracy for
constant-latency parallelism is the right call here.
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.common.domain.interfaces.use_case import UseCase
from src.dashboard.domain.entities.processing import ProcessingData
from src.dashboard.domain.repositories.dashboard_metrics import (
    DashboardMetricsRepository,
)


@dataclass
class GetProcessing(UseCase):
    tenant_id: UUID
    tenant_time_zone: str
    live_limit: int
    dashboard_metrics_repository: DashboardMetricsRepository

    async def execute(self) -> ProcessingData:
        now = datetime.now(UTC)
        # Phase 1: summary + stages in parallel.
        summary, stages = await asyncio.gather(
            self.dashboard_metrics_repository.get_processing_summary(
                tenant_id=self.tenant_id,
                now=now,
                time_zone=self.tenant_time_zone,
            ),
            self.dashboard_metrics_repository.list_pipeline_stages(
                tenant_id=self.tenant_id,
            ),
        )
        # Phase 2: live processing needs the avg from the summary to compute
        # ETAs. The avg may be None (no completed docs today); the repo
        # returns eta_seconds=None for every live doc in that case.
        live_processing = await self.dashboard_metrics_repository.list_live_processing(
            tenant_id=self.tenant_id,
            limit=self.live_limit,
            avg_processing_seconds=summary.avg_processing_seconds,
            now=now,
        )
        return ProcessingData(
            summary=summary,
            stages=stages,
            live_processing=live_processing,
        )
