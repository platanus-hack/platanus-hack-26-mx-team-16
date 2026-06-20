from dataclasses import dataclass
from uuid import UUID

from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.enums.tenants import TenantRoleStatus
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.permissions.roles import DEFAULT_TENANT_ROLES
from src.tenants.application.use_cases.role.creator import TenantRoleCreator
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository


@dataclass
class TenantRolesBootstrapper(UseCase):
    tenant_id: UUID
    role_repository: TenantRoleRepository

    async def execute(self) -> list[TenantRole]:
        created_roles: list[TenantRole] = []

        for role_definition in DEFAULT_TENANT_ROLES:
            tenant_role = await self.role_repository.find_by_slug(
                tenant_id=self.tenant_id,
                slug=role_definition.slug,
            )
            if tenant_role:
                tenant_role.permissions = role_definition.permissions
                tenant_role.activate()
                await self.role_repository.persist(tenant_role)
                continue

            tenant_role = await TenantRoleCreator(
                tenant_id=self.tenant_id,
                name=role_definition.name,
                slug=role_definition.slug,
                status=TenantRoleStatus.ACTIVE,
                permissions=role_definition.permissions,
                icon_url=role_definition.icon_url,
                role_repository=self.role_repository,
            ).execute()
            created_roles.append(tenant_role)

        return created_roles
