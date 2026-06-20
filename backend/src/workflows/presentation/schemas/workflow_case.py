from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.enums.workflow_cases import WorkflowCaseStatus


class CreateWorkflowCaseRequest(CamelCaseRequest):
    name: str = Field(..., min_length=1, max_length=255)


class UpdateWorkflowCaseRequest(CamelCaseRequest):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: WorkflowCaseStatus | None = Field(default=None)
