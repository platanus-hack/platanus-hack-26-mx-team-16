from src.common.application.commands.users import (
    DeleteTenantUserCommand,
    PersistTenantUserCommand,
    PersistUserCommand,
    SetupTenantUserCommand,
    SetUserCurrentTenantCommand,
    SetUserPasswordCommand,
    UpdateUserPasswordCommand,
)
from src.common.application.queries.users import (
    CheckPasswordQuery,
    GetOrCreateTenantUserQuery,
    GetOrCreateUserQuery,
    GetTenantUserByIdQuery,
    GetUserByEmailQuery,
    GetUserByIdQuery,
    GetUserByPhoneNumberQuery,
)
from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.users.application.commands.delete_tenant_user import DeleteTenantUserHandler
from src.users.application.commands.persist_tenant_user import PersistTenantUserHandler
from src.users.application.commands.persist_user import PersistUserHandler
from src.users.application.commands.set_current_tenant import SetUserCurrentTenantHandler
from src.users.application.commands.set_password import SetUserPasswordHandler
from src.users.application.commands.setup_tenant_user import SetupTenantUserHandler
from src.users.application.commands.update_password import UpdateUserPasswordHandler
from src.users.application.queries.check_password import CheckPasswordQueryHandler
from src.users.application.queries.get_tenant_user import GetOrCreateTenantUserHandler, GetTenantUserByIdHandler
from src.users.application.queries.get_user import (
    GetOrCreateUserHandler,
    GetUserByEmailHandler,
    GetUserByIdHandler,
    GetUserByPhoneNumberHandler,
)


def users_wiring(
    domain: DomainContext,
    bus: BusContext,
) -> None:
    # ->  Q U E R I E S
    bus.query_bus.subscribe(
        query=GetOrCreateUserQuery,
        handler=GetOrCreateUserHandler(
            user_repository=domain.user_repository,
            email_repository=domain.email_repository,
            query_bus=bus.query_bus,
        ),
    )
    bus.query_bus.subscribe(
        query=CheckPasswordQuery,
        handler=CheckPasswordQueryHandler(
            user_repository=domain.user_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetUserByEmailQuery,
        handler=GetUserByEmailHandler(
            user_repository=domain.user_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetUserByIdQuery,
        handler=GetUserByIdHandler(
            user_repository=domain.user_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetUserByPhoneNumberQuery,
        handler=GetUserByPhoneNumberHandler(
            user_repository=domain.user_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetOrCreateTenantUserQuery,
        handler=GetOrCreateTenantUserHandler(
            tenant_user_repository=domain.tenant_user_repository,
        ),
    )
    bus.query_bus.subscribe(
        query=GetTenantUserByIdQuery,
        handler=GetTenantUserByIdHandler(
            tenant_user_repository=domain.tenant_user_repository,
        ),
    )

    # ->  C O M M A N D S

    bus.command_bus.subscribe(
        command=SetUserCurrentTenantCommand,
        handler=SetUserCurrentTenantHandler(
            user_repository=domain.user_repository,
            query_bus=bus.query_bus,
        ),
    )
    bus.command_bus.subscribe(
        command=PersistUserCommand,
        handler=PersistUserHandler(
            user_repository=domain.user_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=UpdateUserPasswordCommand,
        handler=UpdateUserPasswordHandler(
            user_repository=domain.user_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=SetupTenantUserCommand,
        handler=SetupTenantUserHandler(
            repository=domain.tenant_user_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=SetUserPasswordCommand,
        handler=SetUserPasswordHandler(
            repository=domain.user_repository,
            query_bus=bus.query_bus,
        ),
    )
    bus.command_bus.subscribe(
        command=DeleteTenantUserCommand,
        handler=DeleteTenantUserHandler(
            tenant_user_repository=domain.tenant_user_repository,
        ),
    )
    bus.command_bus.subscribe(
        command=PersistTenantUserCommand,
        handler=PersistTenantUserHandler(
            tenant_user_repository=domain.tenant_user_repository,
        ),
    )
