from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from expects import be_a, be_none, equal, expect, raise_error

from src.auth.application.use_cases.session_builder import (
    TenantUserProfileBuilder,
    TenantUserSessionBuilder,
)
from src.common.application.queries.tenants import GetTenantUserQuery, GetUserTenantQuery
from src.common.application.queries.users import CheckPasswordQuery, GetUserByEmailQuery
from src.common.domain.entities.auth.user_session import TenantUserProfile, TenantUserSession
from src.common.domain.exceptions.auth import InvalidCredentialsError
from src.common.domain.exceptions.users import UserNotFoundError


# ── TenantUserSessionBuilder ──


@pytest.fixture
def session_builder(query_bus, token_service):
    return TenantUserSessionBuilder(
        email="test@example.com",
        password="password123",
        query_bus=query_bus,
        token_service=token_service,
    )


async def test_execute__returns_tenant_user_session(
    session_builder, user, jwt_session, query_bus_with_tenant_session, token_service, tenant, tenant_user
):
    session_builder.query_bus = query_bus_with_tenant_session

    async def ask_side_effect(query):
        if isinstance(query, GetUserByEmailQuery):
            return user
        if isinstance(query, CheckPasswordQuery):
            return True
        if isinstance(query, GetUserTenantQuery):
            return tenant
        if isinstance(query, GetTenantUserQuery):
            return tenant_user
        return None

    session_builder.query_bus.ask = AsyncMock(side_effect=ask_side_effect)
    token_service.generate_token.return_value = jwt_session

    result = await session_builder.execute()

    expect(result).to(be_a(TenantUserSession))
    expect(result.session).to(equal(jwt_session))
    expect(result.user).to(equal(user))
    expect(result.tenant).to(equal(tenant))


async def test_execute__user_not_found_raises(session_builder):
    session_builder.query_bus.ask = AsyncMock(return_value=None)

    with pytest.raises(UserNotFoundError):
        await session_builder.execute()


async def test_execute__wrong_password_raises(session_builder, user):
    async def ask_side_effect(query):
        if isinstance(query, GetUserByEmailQuery):
            return user
        if isinstance(query, CheckPasswordQuery):
            return False
        return None

    session_builder.query_bus.ask = AsyncMock(side_effect=ask_side_effect)

    with pytest.raises(InvalidCredentialsError):
        await session_builder.execute()


async def test_execute__generates_token_with_user_namespace(session_builder, user, jwt_session, tenant, tenant_user):
    async def ask_side_effect(query):
        if isinstance(query, GetUserByEmailQuery):
            return user
        if isinstance(query, CheckPasswordQuery):
            return True
        if isinstance(query, GetUserTenantQuery):
            return tenant
        if isinstance(query, GetTenantUserQuery):
            return tenant_user
        return None

    session_builder.query_bus.ask = AsyncMock(side_effect=ask_side_effect)
    session_builder.token_service.generate_token.return_value = jwt_session

    await session_builder.execute()

    session_builder.token_service.generate_token.assert_called_once_with(
        sub=str(user.uuid),
        namespace="USER",
        # E5 · ADR 0001: sin repo staff inyectado jamás se emite el claim.
        extra_claims=None,
    )


async def test_execute__no_tenant_returns_session_with_none_tenant(session_builder, user, jwt_session):
    async def ask_side_effect(query):
        if isinstance(query, GetUserByEmailQuery):
            return user
        if isinstance(query, CheckPasswordQuery):
            return True
        if isinstance(query, GetUserTenantQuery):
            return None
        return None

    session_builder.query_bus.ask = AsyncMock(side_effect=ask_side_effect)
    session_builder.token_service.generate_token.return_value = jwt_session

    result = await session_builder.execute()

    expect(result).to(be_a(TenantUserSession))
    expect(result.tenant).to(be_none)
    expect(result.tenant_role).to(be_none)


# ── TenantUserProfileBuilder ──


@pytest.fixture
def profile_builder(query_bus, user):
    return TenantUserProfileBuilder(
        user=user,
        query_bus=query_bus,
    )


async def test_profile__returns_tenant_user_profile(profile_builder, tenant, tenant_user, tenant_role_meta):
    async def ask_side_effect(query):
        if isinstance(query, GetUserTenantQuery):
            return tenant
        if isinstance(query, GetTenantUserQuery):
            return tenant_user
        return None

    profile_builder.query_bus.ask = AsyncMock(side_effect=ask_side_effect)

    result = await profile_builder.execute()

    expect(result).to(be_a(TenantUserProfile))
    expect(result.tenant).to(equal(tenant))
    expect(result.tenant_role).to(equal(tenant_role_meta))


async def test_profile__no_tenant_returns_none_fields(profile_builder):
    profile_builder.query_bus.ask = AsyncMock(return_value=None)

    result = await profile_builder.execute()

    expect(result).to(be_a(TenantUserProfile))
    expect(result.tenant).to(be_none)
    expect(result.tenant_role).to(be_none)
