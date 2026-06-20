from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.workflow_rules import (
    WorkflowAnalysisRunStatus,
    WorkflowAnalysisRunTrigger,
)


class WorkflowAnalysisRun(BaseModel):
    """One execution of analysis over a case (renamed from AnalysisRun)."""

    uuid: UUID = Field(default_factory=uuid4)
    tenant_id: UUID = Field(...)
    workflow_id: UUID = Field(...)
    workflow_case_id: UUID = Field(...)
    status: WorkflowAnalysisRunStatus = Field(default=WorkflowAnalysisRunStatus.RUNNING)
    trigger: WorkflowAnalysisRunTrigger = Field(default=WorkflowAnalysisRunTrigger.USER)
    triggered_by: UUID | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    canceled_at: datetime | None = Field(default=None)
    canceled_by: UUID | None = Field(default=None)
    error: str | None = Field(default=None)

    reviewer_model: dict | None = Field(default=None)
    critic_model: dict | None = Field(default=None)
    consensus_samples: int | None = Field(default=None)

    rules_total: int | None = Field(default=None)
    rules_passed: int | None = Field(default=None)
    rules_failed: int | None = Field(default=None)
    rules_inconclusive: int | None = Field(default=None)

    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    @property
    def duration_ms(self) -> int | None:
        if self.started_at is None:
            return None
        end = self.completed_at or self.canceled_at
        if end is None:
            return None
        return int((end - self.started_at).total_seconds() * 1000)

    @property
    def persist_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "workflow_id": self.workflow_id,
            "workflow_case_id": self.workflow_case_id,
            "status": self.status,
            "trigger": self.trigger,
            "triggered_by": self.triggered_by,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "canceled_at": self.canceled_at,
            "canceled_by": self.canceled_by,
            "error": self.error,
            "reviewer_model": self.reviewer_model,
            "critic_model": self.critic_model,
            "consensus_samples": self.consensus_samples,
            "rules_total": self.rules_total,
            "rules_passed": self.rules_passed,
            "rules_failed": self.rules_failed,
            "rules_inconclusive": self.rules_inconclusive,
        }
