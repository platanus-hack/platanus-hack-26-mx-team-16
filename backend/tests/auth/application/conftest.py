from unittest.mock import AsyncMock, create_autospec
from uuid import uuid4

import pytest

from src.common.application.helpers.datetimes import utc_now
from src.common.domain.buses.queries import QueryBus
from src.common.domain.entities.common.jtw_session import JwtSession
from src.common.domain.models.email_address import EmailAddress
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.entities.tenants.tenant_role import TenantRoleMeta
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.models.user import User
from src.common.domain.enums.tenants import TenantRoleStatus, TenantStatus
from src.common.domain.enums.users import TenantUserStatus
from src.common.domain.services.token_service import TokenService


@pytest.fixture
def query_bus():
    return create_autospec(spec=QueryBus, spec_set=True, instance=True)


@pytest.fixture
def token_service():
    return create_autospec(spec=TokenService, spec_set=True, instance=True)


@pytest.fixture
def user():
    return User(
        uuid=uuid4(),
        username="testuser",
        first_name="Test",
        last_name="User",
        email_address=EmailAddress(
            uuid=uuid4(),
            email="test@example.com",
            is_verified=True,
        ),
    )


@pytest.fixture
def tenant():
    return Tenant(
        uuid=uuid4(),
        owner_id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
        status=TenantStatus.ACTIVE,
        created_at=utc_now(),
        updated_at=utc_now(),
    )


@pytest.fixture
def tenant_role_meta():
    return TenantRoleMeta(
        name="Owner",
        status=TenantRoleStatus.ACTIVE,
        slug="owner",
        is_owner=True,
        permissions=[],
    )


@pytest.fixture
def tenant_user(tenant, user, tenant_role_meta):
    return TenantUser(
        uuid=uuid4(),
        tenant_id=tenant.uuid,
        user_id=user.uuid,
        is_owner=True,
        status=TenantUserStatus.ACTIVE,
        first_name="Test",
        last_name="User",
        tenant_role_meta=tenant_role_meta,
    )


@pytest.fixture
def jwt_session():
    return JwtSession(
        access_token="access.token.here",
        refresh_token="refresh.token.here",
    )


@pytest.fixture
def query_bus_with_tenant_session(query_bus, tenant, tenant_user):
    """Query bus that returns tenant and tenant_user for session params lookups."""

    async def ask_side_effect(query):
        from src.common.application.queries.tenants import GetTenantUserQuery, GetUserTenantQuery

        if isinstance(query, GetUserTenantQuery):
            return tenant
        if isinstance(query, GetTenantUserQuery):
            return tenant_user
        return None

    query_bus.ask = AsyncMock(side_effect=ask_side_effect)
    return query_bus
