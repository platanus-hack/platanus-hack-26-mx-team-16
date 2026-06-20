"""Domain model for the unified ``HumanTask`` (F6).

A durable pause point. ``audience`` (a free string like ``doxiq_analyst`` /
``bank_analyst``) + RBAC decides who sees it — circulares chains two with
different audiences (B4). ``assignee_mode`` decides who resolves it (an internal
queue vs an external callback). The pipeline run waits on the ``task_resolved``
signal keyed by ``task_key`` (deterministic per run+phase).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.human_tasks import (
    HumanTaskAssigneeMode,
    HumanTaskKind,
    HumanTaskStatus,
)


class HumanTask(BaseModel):
    uuid: UUID
    tenant_id: UUID
    # Deterministic per (workflow run, phase) so the workflow can wait/resume.
    task_key: str
    kind: HumanTaskKind
    status: HumanTaskStatus = HumanTaskStatus.PENDING
    assignee_mode: HumanTaskAssigneeMode = HumanTaskAssigneeMode.INTERNAL_QUEUE
    audience: str | None = None
    workflow_id: UUID | None = None
    case_id: UUID | None = None
    pipeline_run_id: str | None = None  # Temporal workflow id
    payload: dict = Field(default_factory=dict)
    resolution: dict | None = None
    expires_at: datetime | None = None
    # E5 · revisión multinivel: "review_l1" | "review_l2"; None = gate único E4.
    stage: str | None = None
    # E5 · claim/lock pesimista: "user:<uuid>" | "staff:<uuid>".
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")
