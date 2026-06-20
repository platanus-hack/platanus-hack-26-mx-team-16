"""Pydantic request schemas for the WorkflowProcessingJob endpoints."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DispatchWorkflowProcessingJobRequest(BaseModel):
    file_id: UUID = Field(..., alias="fileId")
    workflow_case_id: UUID | None = Field(default=None, alias="workflowCaseId")

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
