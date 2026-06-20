from dataclasses import dataclass
from uuid import UUID

from src.common.domain.buses.queries import Query
from src.common.domain.enums.users import TenantUserStatus


@dataclass
class GetUserTenantsQuery(Query):
    user_id: UUID


@dataclass
class GetUserTenantQuery(Query):
    user_id: UUID


@dataclass
class GetTenantByIdQuery(Query):
    tenant_id: UUID


@dataclass
class GetTenantUserQuery(Query):
    user_id: UUID
    tenant_id: UUID
    status: TenantUserStatus | None = None


@dataclass
class GetTenantRoleByIdQuery(Query):
    tenant_role_id: UUID


@dataclass
class RemoveTenantByIdQuery(Query):
    tenant_id: UUID
