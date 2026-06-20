from dataclasses import asdict, dataclass
from typing import Any, Self
from uuid import UUID

from src.common.domain.buses.commands import Command
from src.common.domain.models.tenants.tenant import Tenant


@dataclass
class PersistTenantCommand(Command):
    tenant: Tenant

    @property
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(**kwargs)


@dataclass
class BootstrapTenantRolesCommand(Command):
    tenant_id: UUID

    @property
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(**kwargs)


@dataclass
class AssignTenantRoleInBatchCommand(Command):
    tenant_id: UUID

    @property
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(**kwargs)


@dataclass
class SoftDeleteTenantCommand(Command):
    tenant_id: UUID

    @property
    def to_dict(self) -> dict[str, Any]:
        return {"tenant_id": str(self.tenant_id)}

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Self:
        return cls(tenant_id=UUID(kwargs["tenant_id"]))
