from src.common.application.commands.tenants import (
    AssignTenantRoleInBatchCommand,
    BootstrapTenantRolesCommand,
    PersistTenantCommand,
    SoftDeleteTenantCommand,
)
from src.common.application.queries.tenants import (
    GetTenantByIdQuery,
    GetTenantRoleByIdQuery,
    GetTenantUserQuery,
    GetUserTenantQuery,
    GetUserTenantsQuery,
)
from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.tenants.application.command.persist_tenant import PersistTenantHandler
from src.tenants.application.command.soft_delete_tenant import SoftDeleteTenantHandler
from src.tenants.application.command.roles.assign_role_in_batch import AssignTenantRolenBatchHandler
from src.tenants.application.command.roles.bootstrap_roles import BootstrapTenantRolesHandler
from src.tenants.application.queries.tenants.get_tenant import GetTenantByIdHandler
from src.tenants.application.queries.tenants.get_tenant_role import GetTenantRoleByIdHandler
from src.tenants.application.queries.tenants.get_tenant_user import GetTenantUserHandler
from src.tenants.application.queries.tenants.get_user_tenant import GetUserTenantHandler
from src.tenants.application.queries.tenants.get_user_tenants import GetUserTenantsHandler


def tenants_wiring(
    domain: DomainContext,
    bus: BusContext,
):
    #  C O M M A N D S
    bus.command_bus.subscribe(
        command=PersistTenantCommand,
        handler=PersistTenantHandler(
            repository=domain.tenant_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=BootstrapTenantRolesCommand,
        handler=BootstrapTenantRolesHandler(
            role_repository=domain.tenant_role_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=SoftDeleteTenantCommand,
        handler=SoftDeleteTenantHandler(
            tenant_repository=domain.tenant_repository,
            user_repository=domain.user_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=AssignTenantRoleInBatchCommand,
        handler=AssignTenantRolenBatchHandler(
            role_repository=domain.tenant_role_repository,
            tenant_user_repository=domain.tenant_user_repository,
            tenant_repository=domain.tenant_repository,
        ),
    )

    #  Q U E R I E S

    # -> Tenants
    bus.query_bus.subscribe(
        query=GetUserTenantsQuery,
        handler=GetUserTenantsHandler(
            repository=domain.tenant_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetUserTenantQuery,
        handler=GetUserTenantHandler(
            repository=domain.tenant_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetTenantByIdQuery,
        handler=GetTenantByIdHandler(
            repository=domain.tenant_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetTenantUserQuery,
        handler=GetTenantUserHandler(
            repository=domain.tenant_user_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetTenantRoleByIdQuery,
        handler=GetTenantRoleByIdHandler(
            tenant_role_repository=domain.tenant_role_repository,
        ),
    )
