from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.workflow_rules import WorkflowRuleResultStatus
from src.common.domain.models.processing.citation import Citation


class WorkflowRuleResult(BaseModel):
    """One evaluation outcome of a WorkflowRule (spec §3.3)."""

    uuid: UUID = Field(default_factory=uuid4)
    tenant_id: UUID = Field(...)
    workflow_analysis_run_id: UUID = Field(...)
    rule_id: UUID = Field(...)
    case_id: UUID = Field(...)
    kind: str = Field(...)
    status: WorkflowRuleResultStatus = Field(default=WorkflowRuleResultStatus.SUCCESS)
    output: dict[str, Any] | None = Field(default=None)
    reasoning: str | None = Field(default=None)
    citations: list[Citation] = Field(default_factory=list)
    document_refs: dict[str, Any] = Field(default_factory=dict)
    document_refs_hash: str = Field(...)
    rendered_prompt: str | None = Field(default=None)
    evaluation_metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(from_attributes=True, extra="ignore")
