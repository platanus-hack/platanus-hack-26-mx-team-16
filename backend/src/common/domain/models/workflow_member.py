"""Domain model for ``WorkflowMember`` — an explicit per-workflow member grant.

Members gate access to ``private`` workflows. The persisted row only carries
``user_id`` + ``role``; the name / email / photo fields are enrichment populated
on read from the member's tenant-user profile (never persisted here).
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.models.processing.workflow import WorkflowAccessType

WorkflowMemberRole = Literal["admin", "member", "viewer"]


class WorkflowMember(BaseModel):
    uuid: UUID
    tenant_id: UUID
    workflow_id: UUID
    user_id: UUID
    role: WorkflowMemberRole = "member"

    # Enrichment from the tenant-user profile (read-only; not persisted here).
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    photo: str | None = None
    is_owner: bool = False

    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    @property
    def full_name(self) -> str:
        name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return name or (self.email or "")


class WorkflowPermissions(BaseModel):
    """The full access-control view for a workflow: its access mode + members."""

    workflow_id: UUID
    access_type: WorkflowAccessType
    members: list[WorkflowMember] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, extra="ignore")
