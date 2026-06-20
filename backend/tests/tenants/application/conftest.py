"""Mocked dependencies for tenants application-layer use cases.

Every repository and service consumed by a tenant or invitation use case
is wired here with `create_autospec` so each test can override only the
return values it cares about, without bringing the real DB into scope.
"""

from unittest.mock import AsyncMock, create_autospec

import pytest

from src.common.domain.buses.commands import CommandBus
from src.common.domain.entities.common.jtw_session import JwtSession
from src.common.domain.services.token_service import TokenService
from src.industries.domain.repositories.industry_repository import IndustryRepository
from src.tenants.domain.repositories.tenant import TenantRepository
from src.tenants.domain.repositories.tenant_role import TenantRoleRepository
from src.tenants.domain.repositories.tenant_user import TenantUserRepository
from src.tenants.domain.repositories.tenant_user_invitation import (
    TenantUserInvitationRepository,
)
from src.users.domain.repositories.email_address import EmailAddressRepository
from src.users.domain.repositories.user import UserRepository


@pytest.fixture
def tenant_repository():
    return create_autospec(spec=TenantRepository, spec_set=True, instance=True)


@pytest.fixture
def tenant_role_repository():
    return create_autospec(spec=TenantRoleRepository, spec_set=True, instance=True)


@pytest.fixture
def tenant_user_repository():
    return create_autospec(spec=TenantUserRepository, spec_set=True, instance=True)


@pytest.fixture
def tenant_user_invitation_repository():
    return create_autospec(spec=TenantUserInvitationRepository, spec_set=True, instance=True)


@pytest.fixture
def user_repository():
    return create_autospec(spec=UserRepository, spec_set=True, instance=True)


@pytest.fixture
def email_repository():
    return create_autospec(spec=EmailAddressRepository, spec_set=True, instance=True)


@pytest.fixture
def industry_repository():
    return create_autospec(spec=IndustryRepository, spec_set=True, instance=True)


@pytest.fixture
def token_service():
    service = create_autospec(spec=TokenService, spec_set=True, instance=True)
    service.generate_token.return_value = JwtSession(
        access_token="test-access-token",  # noqa: S106 — test fixture
        refresh_token="test-refresh-token",  # noqa: S106 — test fixture
    )
    return service


@pytest.fixture
def command_bus():
    """`CommandBus.dispatch` is async — `create_autospec` already returns
    AsyncMock for async methods, but we set it explicitly to keep call
    assertions readable in the tests."""
    bus = create_autospec(spec=CommandBus, spec_set=True, instance=True)
    bus.dispatch = AsyncMock(return_value=None)
    return bus
