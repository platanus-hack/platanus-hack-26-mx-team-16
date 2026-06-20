import uuid
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.common.domain.models.email_address import EmailAddress
from src.common.domain.models.phone_number import PhoneNumber
from src.common.domain.models.tenants.tenant_role import TenantRole


class User(BaseModel):
    uuid: UUID
    username: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: PhoneNumber | None = None
    email_address: EmailAddress | None = None
    current_tenant_id: UUID | None = None
    role: TenantRole | None = None
    has_password: bool = False
    is_superuser: bool = False

    model_config = ConfigDict(
        from_attributes=True,
    )

    @property
    def persist_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
        }
        if self.email_address:
            data["email_address_id"] = self.email_address.uuid
        if self.phone_number:
            data["phone_number_id"] = self.phone_number.uuid
        return data

    @property
    def token_data(self) -> dict[str, Any]:
        return {
            "sub": str(self.uuid),
            "email": (self.email_address.email if self.email_address else None),
            "phone_number": (self.phone_number.international_phone_number if self.phone_number else None),
        }

    @classmethod
    def from_raw(cls, email: str, first_name: str | None = None, last_name: str | None = None) -> Self:
        return cls(
            uuid=uuid.uuid4(),
            username=str(uuid.uuid4().hex),
            email_address=EmailAddress(
                uuid=uuid.uuid4(),
                email=email,
            ),
            first_name=first_name,
            last_name=last_name,
        )
