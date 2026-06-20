from dataclasses import asdict, dataclass, field
from typing import Any, Self
from uuid import UUID

from src.common.domain.buses.commands import Command
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.common.domain.enums.users import TenantUserStatus


@dataclass
class SetUserCurrentTenantCommand(Command):
    user_id: UUID
    tenant_id: UUID

    @property
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(**kwargs)


@dataclass
class PersistUserCommand(Command):
    user: User

    @property
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(**kwargs)


@dataclass
class UpdateUserPasswordCommand(Command):
    user_id: UUID
    current_password: str
    new_password: str

    @property
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(**kwargs)


@dataclass
class SetUserPasswordCommand(Command):
    user_id: UUID
    password: str

    @property
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(**kwargs)


@dataclass
class MergeTenantsCommand(Command):
    from_tenant_id: UUID
    to_tenant_id: UUID

    @property
    def to_dict(self) -> dict[str, Any]:
        return {"from_tenant_id": str(self.from_tenant_id), "to_tenant_id": str(self.to_tenant_id)}

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(
            from_tenant_id=UUID(kwargs["from_tenant_id"]),
            to_tenant_id=UUID(kwargs["to_tenant_id"]),
        )


@dataclass
class SetupTenantUserCommand(Command):
    tenant_id: UUID
    user_id: UUID
    status: TenantUserStatus = TenantUserStatus.ACTIVE
    is_owner: bool = False
    tenant_role_id: UUID | None = None
    permissions: list[str] = field(default_factory=list)

    @property
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict) -> "SetupTenantUserCommand":
        return cls(**kwargs)


@dataclass
class PersistTenantUserCommand(Command):
    tenant_user: TenantUser

    @property
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(**kwargs)


@dataclass
class DeleteTenantUserCommand(Command):
    tenant_user_id: UUID

    @property
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(**kwargs)
