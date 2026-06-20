from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.common.application.logging import get_logger
from src.common.domain.enums.run_summary import NarrativeStatus
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)

logger = get_logger(__name__)


class SummaryWebhookDispatcher(Protocol):
    async def dispatch(self, *, run_id: UUID, summary: WorkflowAnalysisRunSummary) -> None: ...


class NoopSummaryWebhookDispatcher:
    """Default dispatcher — logs and exits. Replace once `integrations` lands."""

    async def dispatch(self, *, run_id: UUID, summary: WorkflowAnalysisRunSummary) -> None:
        if summary.narrative_status != NarrativeStatus.COMPLETED:
            return
        logger.info(
            "run_summary.webhook_dispatch_noop",
            run_id=str(run_id),
            narrative_status=summary.narrative_status.value,
            verdict=summary.verdict.value,
        )
