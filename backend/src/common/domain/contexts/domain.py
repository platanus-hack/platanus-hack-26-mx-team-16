from dataclasses import dataclass

from src.assets.domain.services.storage import StorageService
from src.common.domain.services.token_service import TokenService
from src.tenants.domain.repositories.tenant import TenantRepository
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository
from src.tenants.domain.repositories.tenant_user import TenantUserRepository
from src.tenants.domain.repositories.tenant_user_invitation import (
    TenantUserInvitationRepository,
)
from src.users.domain.repositories.email_address import EmailAddressRepository
from src.users.domain.repositories.phone_number import PhoneNumberRepository
from src.users.domain.repositories.user import UserRepository


@dataclass
class DomainContext:
    # -> USERS
    user_repository: UserRepository
    email_repository: EmailAddressRepository
    phone_repository: PhoneNumberRepository
    tenant_user_repository: TenantUserRepository

    # -> TENANTS
    tenant_repository: TenantRepository
    tenant_role_repository: TenantRoleRepository
    tenant_user_invitation_repository: TenantUserInvitationRepository

    # -> COMMON
    token_service: TokenService

    # -> ASSETS
    storage_service: StorageService
