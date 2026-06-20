from uuid import uuid4

import pytest
from expects import be_a, equal, expect

from src.common.application.commands.tenants import BootstrapTenantRolesCommand
from src.common.domain.enums.countries import CountryIsoCode
from src.common.domain.enums.tenants import TenantStatus
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.exceptions.tenants import TenantLimitExcedeedError
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.tenants.application.use_cases.tenant.registerer import TenantRegisterer


@pytest.fixture
def owner():
    return User(
        uuid=uuid4(),
        username="owner",
        first_name="Owner",
        last_name="One",
    )


@pytest.fixture
def use_case(
    owner,
    tenant_repository,
    tenant_role_repository,
    tenant_user_repository,
    user_repository,
    command_bus,
):
    tenant_repository.filter_by_user.return_value = []
    tenant_repository.get_slug_count.return_value = 0
    tenant_repository.persist.side_effect = lambda instance: instance
    tenant_user_repository.persist.side_effect = lambda instance: instance
    user_repository.update_current_tenant.return_value = None
    return TenantRegisterer(
        name="Acme Corp",
        owner=owner,
        country_code=CountryIsoCode.MEXICO,
        tenant_repository=tenant_repository,
        tenant_role_repository=tenant_role_repository,
        command_bus=command_bus,
        user_repository=user_repository,
        tenant_user_repository=tenant_user_repository,
    )


async def test_execute__persists_tenant_with_expected_fields(use_case, owner, tenant_repository):
    result = await use_case.execute()

    expect(result).to(be_a(Tenant))
    expect(result.name).to(equal("Acme Corp"))
    expect(result.slug).to(equal("acme-corp"))
    expect(result.owner_id).to(equal(owner.uuid))
    expect(result.status).to(equal(TenantStatus.ACTIVE))
    tenant_repository.persist.assert_called_once()


async def test_execute__bootstraps_default_roles_via_command_bus(use_case, command_bus):
    result = await use_case.execute()

    command_bus.dispatch.assert_called_once()
    command = command_bus.dispatch.call_args.kwargs["command"]
    expect(command).to(be_a(BootstrapTenantRolesCommand))
    expect(command.tenant_id).to(equal(result.uuid))


async def test_execute__creates_owner_tenant_user_with_is_owner_true(use_case, owner, tenant_user_repository):
    result = await use_case.execute()

    tenant_user_repository.persist.assert_called_once()
    persisted = tenant_user_repository.persist.call_args.args[0]
    expect(persisted).to(be_a(TenantUser))
    expect(persisted.user_id).to(equal(owner.uuid))
    expect(persisted.tenant_id).to(equal(result.uuid))
    expect(persisted.is_owner).to(equal(True))
    expect(persisted.status).to(equal(TenantUserStatus.ACTIVE))
    expect(persisted.first_name).to(equal(owner.first_name))
    expect(persisted.last_name).to(equal(owner.last_name))


async def test_execute__updates_owner_current_tenant(use_case, owner, user_repository):
    result = await use_case.execute()

    user_repository.update_current_tenant.assert_called_once_with(user_id=owner.uuid, tenant_id=result.uuid)


async def test_execute__appends_suffix_when_slug_already_taken(use_case, tenant_repository):
    tenant_repository.get_slug_count.return_value = 2

    result = await use_case.execute()

    expect(result.slug).to(equal("acme-corp-2"))


async def test_execute__over_tenants_limit_raises(use_case, tenant_repository):
    use_case.tenants_limit = 1
    tenant_repository.filter_by_user.return_value = [object(), object()]

    with pytest.raises(TenantLimitExcedeedError):
        await use_case.execute()

    tenant_repository.persist.assert_not_called()
