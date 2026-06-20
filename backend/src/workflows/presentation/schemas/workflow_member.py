from typing import Literal
from uuid import UUID

from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest


class SetAccessTypeRequest(CamelCaseRequest):
    access_type: Literal["organization", "private"] = Field(...)


class AddMemberRequest(CamelCaseRequest):
    user_id: UUID = Field(...)
    role: Literal["admin", "member", "viewer"] = Field(default="member")


class UpdateMemberRoleRequest(CamelCaseRequest):
    role: Literal["admin", "member", "viewer"] = Field(...)
