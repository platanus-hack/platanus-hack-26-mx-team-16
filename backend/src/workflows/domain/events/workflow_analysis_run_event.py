"""Domain events for the workflow-analysis-run SSE stream.

One event type per spec §12. Each event lands on a per-run Redis channel;
subscribers only need the run_id to listen.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from src.common.domain.events.base import Event

WorkflowAnalysisRunEventType = Literal[
    "RUN_STARTED",
    "EVALUATION_STARTED",
    "STAGE_PROGRESS",
    "RULE_RESULT_READY",
    "RUN_PROGRESS",
    "RUN_COMPLETED",
    "RUN_FAILED",
    "RUN_CANCELED",
    "HEARTBEAT",
]

RUN_TERMINAL_EVENT_TYPES: frozenset[WorkflowAnalysisRunEventType] = frozenset(
    {"RUN_COMPLETED", "RUN_FAILED", "RUN_CANCELED"}
)


def channel_for_run(run_id: UUID) -> str:
    return f"workflow_analysis_run:{run_id.hex}:events"


class WorkflowAnalysisRunEvent(Event):
    type: WorkflowAnalysisRunEventType
    run_id: UUID

    @property
    def channel(self) -> str:
        return channel_for_run(self.run_id)
