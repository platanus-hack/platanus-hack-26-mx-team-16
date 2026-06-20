"""Domain events for the run-summary SSE stream (synthesis spec §7).

Events land on a per-run channel — re-uses the same channel as the
analysis-run events to keep one socket per run for the UI.
"""

from typing import Literal
from uuid import UUID

from src.common.domain.events.base import Event
from src.workflows.domain.events.workflow_analysis_run_event import channel_for_run

RunSummaryEventType = Literal[
    "summary.verdict_ready",
    "summary.narrative_started",
    "summary.narrative_completed",
    "summary.failed",
]

SUMMARY_TERMINAL_EVENT_TYPES: frozenset[RunSummaryEventType] = frozenset(
    {"summary.narrative_completed", "summary.failed"}
)


class RunSummaryEvent(Event):
    type: RunSummaryEventType
    run_id: UUID

    @property
    def channel(self) -> str:
        return channel_for_run(self.run_id)
