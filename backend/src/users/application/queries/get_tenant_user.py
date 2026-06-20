import uuid
from dataclasses import dataclass

from src.common.application.queries.users import GetOrCreateTenantUserQuery, GetTenantUserByIdQuery
from src.common.domain.buses.queries import QueryHandler
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.tenants.domain.repositories.tenant_user import TenantUserRepository


@dataclass
class GetOrCreateTenantUserHandler(QueryHandler[GetOrCreateTenantUserQuery, User]):
    tenant_user_repository: TenantUserRepository

    async def execute(self, query: GetOrCreateTenantUserQuery) -> TenantUser:
        tenant_user = await self.tenant_user_repository.find_by_args(
            user_id=query.user.uuid,
            tenant_id=query.tenant_id,
        )
        if tenant_user:
            return tenant_user

        return await self.tenant_user_repository.persist(
            instance=TenantUser(
                uuid=uuid.uuid4(),
                user_id=query.user.uuid,
                tenant_id=query.tenant_id,
                user=query.user,
                first_name=query.user.first_name,
                last_name=query.user.last_name,
                status=query.status,
                is_owner=query.is_owner,
                tenant_role_id=query.tenant_role_id,
            ),
        )


@dataclass
class GetTenantUserByIdHandler(QueryHandler[GetTenantUserByIdQuery, User]):
    tenant_user_repository: TenantUserRepository

    async def execute(self, query: GetTenantUserByIdQuery) -> User | None:
        return await self.tenant_user_repository.find(query.tenant_user_id)
