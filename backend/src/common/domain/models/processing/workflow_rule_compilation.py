from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.workflow_rules import WorkflowRuleCompilationStatus


class WorkflowRuleCompilation(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    rule_id: UUID = Field(...)
    version: int = Field(...)
    kind: str = Field(...)
    status: WorkflowRuleCompilationStatus = Field(default=WorkflowRuleCompilationStatus.PENDING)
    artifact: dict[str, Any] | None = Field(default=None)
    compiled_with: dict[str, Any] | None = Field(default=None)
    error: str | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)

    model_config = ConfigDict(from_attributes=True, extra="ignore")
