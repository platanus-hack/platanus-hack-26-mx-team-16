from uuid import UUID

from pydantic import EmailStr, Field

from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.entities.phone_number import RawPhoneNumber
from src.common.domain.enums.users import TenantUserStatus


class TenantUserParams(CamelCaseRequest):
    email: EmailStr
    password: str
    first_name: str | None = Field(default=None, max_length=150)
    last_name: str | None = Field(default=None, max_length=150)
    status: TenantUserStatus = Field(default=TenantUserStatus.ACTIVE)
    tenant_role_id: UUID | None = Field(default=None)
    phone_number: RawPhoneNumber | None = Field(default=None)
