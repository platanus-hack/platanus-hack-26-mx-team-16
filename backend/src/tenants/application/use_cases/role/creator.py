from dataclasses import dataclass
from uuid import UUID

from slugify import slugify
from uuid6 import uuid7

from src.common.domain.models.tenants.tenant_role import TenantRole
from src.common.domain.enums.tenants import TenantRoleStatus
from src.common.domain.exceptions.tenants import TenantRoleAlreadyExistsError
from src.common.domain.interfaces.use_case import UseCase
from src.tenants.application.helpers.icon_generator import get_default_icon_url
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository


@dataclass
class TenantRoleCreator(UseCase):
    tenant_id: UUID
    name: str
    status: TenantRoleStatus
    permissions: list[str]
    role_repository: TenantRoleRepository
    slug: str | None = None
    icon_url: str | None = None
    force_creation: bool = False

    def __post_init__(self):
        if self.icon_url is None:
            self.icon_url = get_default_icon_url(self.name)

    async def execute(self) -> TenantRole:
        role_slug = self.slug or slugify(self.name)
        existing_role = await self.role_repository.find_by_slug(self.tenant_id, role_slug)

        if existing_role:
            if not self.force_creation:
                raise TenantRoleAlreadyExistsError
            role_slug = f"{role_slug}-{uuid7().hex[-12:]}"

        tenant_role = TenantRole(
            uuid=uuid7(),
            tenant_id=self.tenant_id,
            name=self.name,
            slug=role_slug,
            status=self.status,
            permissions=[str(permission) for permission in self.permissions],
            icon_url=self.icon_url,
        )
        return await self.role_repository.persist(tenant_role)
