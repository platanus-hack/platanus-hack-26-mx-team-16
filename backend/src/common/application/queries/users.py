from dataclasses import dataclass
from uuid import UUID

from src.common.domain.buses.queries import Query
from src.common.domain.entities.phone_number import RawPhoneNumber
from src.common.domain.models.user import User
from src.common.domain.enums.users import TenantUserStatus


@dataclass
class GetOrCreateUserQuery(Query):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    picture: str | None = None
    phone_number: RawPhoneNumber | None = None


@dataclass
class GetUserByEmailQuery(Query):
    email: str


@dataclass
class CheckPasswordQuery(Query):
    user_id: UUID
    raw_password: str


@dataclass
class GetUserByIdQuery(Query):
    user_id: UUID


@dataclass
class GetOrCreateTenantUserQuery(Query):
    tenant_id: UUID
    user: User
    is_owner: bool = False
    tenant_role_id: UUID | None = None
    status: TenantUserStatus = TenantUserStatus.ACTIVE


@dataclass
class GetTenantUserByIdQuery(Query):
    tenant_user_id: UUID


@dataclass
class GetUserByPhoneNumberQuery(Query):
    phone_number: RawPhoneNumber
