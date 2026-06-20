from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.common.domain.enums.tenants import TenantUserInvitationStatus


class TenantUserInvitation(BaseModel):
    uuid: UUID
    tenant_id: UUID
    email: str
    tenant_role_id: UUID | None = None
    token: str
    status: TenantUserInvitationStatus = TenantUserInvitationStatus.PENDING
    expires_at: datetime
    accepted_at: datetime | None = None
    created_by_id: UUID | None = None
    requires_password: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @property
    def is_pending(self) -> bool:
        return self.status == TenantUserInvitationStatus.PENDING

    @property
    def is_expired(self) -> bool:
        return self.status == TenantUserInvitationStatus.EXPIRED

    @property
    def is_accepted(self) -> bool:
        return self.status == TenantUserInvitationStatus.ACCEPTED

    @property
    def persist_data(self) -> dict[str, Any]:
        return {
            "uuid": self.uuid,
            "tenant_id": self.tenant_id,
            "email": self.email,
            "tenant_role_id": self.tenant_role_id,
            "token": self.token,
            "status": self.status.value,
            "expires_at": self.expires_at,
            "accepted_at": self.accepted_at,
            "created_by_id": self.created_by_id,
            "requires_password": self.requires_password,
        }
