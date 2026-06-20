import secrets
import uuid
from dataclasses import dataclass

from slugify import slugify

from src.common.application.commands.tenants import BootstrapTenantRolesCommand
from src.common.application.data.country_configs import CountryConfigBuilder
from src.common.constants import MAX_PAGES, TENANTS_LIMIT
from src.common.domain.buses.commands import CommandBus
from src.common.domain.entities.common.country_config import CountryConfig
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.common.domain.enums.countries import CountryIsoCode
from src.common.domain.enums.tenants import TenantStatus
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.exceptions.tenants import TenantLimitExcedeedError
from src.common.domain.interfaces.use_case import UseCase
from src.tenants.domain.repositories.tenant import TenantRepository
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository
from src.tenants.domain.repositories.tenant_user import TenantUserRepository
from src.users.domain.repositories.user import UserRepository


@dataclass
class TenantRegisterer(UseCase):
    name: str
    owner: User
    country_code: CountryIsoCode
    tenant_repository: TenantRepository
    tenant_role_repository: TenantRoleRepository
    command_bus: CommandBus
    tenants_limit: int = TENANTS_LIMIT
    user_repository: UserRepository = None
    tenant_user_repository: TenantUserRepository = None

    async def execute(self) -> Tenant:
        await self._check_creation_limit()
        draft_tenant = await self._build_tenant()
        tenant = await self.tenant_repository.persist(instance=draft_tenant)

        await self._bootstrap_roles(tenant)
        # self._send_welcome_email(tenant)

        if self.tenant_user_repository:
            tenant_user = TenantUser(
                uuid=uuid.uuid4(),
                user_id=self.owner.uuid,
                tenant_id=tenant.uuid,
                is_owner=True,
                status=TenantUserStatus.ACTIVE,
                first_name=self.owner.first_name,
                last_name=self.owner.last_name,
            )
            await self.tenant_user_repository.persist(tenant_user)

        if self.user_repository:
            await self.user_repository.update_current_tenant(user_id=self.owner.uuid, tenant_id=tenant.uuid)

        return tenant

    async def _check_creation_limit(self):
        user_tenants = await self.tenant_repository.filter_by_user(
            user_id=self.owner.uuid,
        )
        if len(user_tenants) <= self.tenants_limit:
            return
        raise TenantLimitExcedeedError

    async def _build_tenant(self) -> Tenant:
        country_config: CountryConfig = CountryConfigBuilder.from_iso_code(
            iso_code=self.country_code,
        )
        return Tenant(
            uuid=uuid.uuid4(),
            name=self.name,
            slug=await self._get_tenant_slug(),
            time_zone=country_config.time_zone,
            country_code=country_config.iso_code,
            currency_code=country_config.currency_code,
            status=TenantStatus.ACTIVE,
            owner_id=self.owner.uuid,
            is_deleted=False,
            webhook_signature_key=f"whsec_{secrets.token_urlsafe(32)}",
        )

    async def _bootstrap_roles(self, tenant: Tenant):
        await self.command_bus.dispatch(
            command=BootstrapTenantRolesCommand(tenant.uuid),
        )

    async def _get_tenant_slug(self) -> str:
        tenant_slug = slugify(self.name)
        slug_count = await self.tenant_repository.get_slug_count(slug=tenant_slug)
        return f"{tenant_slug}-{slug_count}" if slug_count > 0 else tenant_slug
