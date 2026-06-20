"""SSE domain events for the redesigned rules pipeline (spec §12)."""

from __future__ import annotations

from typing import Literal

from src.common.domain.events.base import Event

from uuid import UUID

WorkflowRuleEventType = Literal[
    "COMPILATION_STARTED",
    "COMPILATION_COMPLETED",
    "COMPILATION_FAILED",
    "COMPILATION_INVALIDATED",
    "RULE_RESULT_COMPLETED",
    "HEARTBEAT",
]


def channel_for_workflow_rules(workflow_id: UUID) -> str:
    return f"workflow:{workflow_id}:workflow_rules:events"


def compiling_rules_key(workflow_id: UUID) -> str:
    """Redis SET that holds rule_ids whose compilation is currently running.

    Frontend reads this on mount to rehydrate the "Interpretando" badge after
    a page refresh.
    """
    return f"workflow:{workflow_id}:workflow_rules:compiling"


class WorkflowRuleEvent(Event):
    type: WorkflowRuleEventType
    workflow_id: UUID
    rule_id: UUID
    compilation_id: UUID | None = None
    error: str | None = None
    reason: str | None = None
    version: int | None = None

    @property
    def channel(self) -> str:
        return channel_for_workflow_rules(self.workflow_id)
