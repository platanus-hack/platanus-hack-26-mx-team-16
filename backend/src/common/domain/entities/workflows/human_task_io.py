"""Activity I/O for opening a durable HumanTask from a pause phase (F6)."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.common.domain.enums.human_tasks import HumanTaskAssigneeMode, HumanTaskKind


class CreateHumanTaskInput(BaseModel):
    task_key: str
    tenant_id: UUID
    kind: HumanTaskKind
    assignee_mode: HumanTaskAssigneeMode = HumanTaskAssigneeMode.INTERNAL_QUEUE
    audience: str | None = None
    workflow_id: UUID | None = None
    case_id: UUID | None = None
    pipeline_run_id: str | None = None
    payload: dict = Field(default_factory=dict)


class CreateHumanTaskOutput(BaseModel):
    task_id: UUID
    task_key: str
