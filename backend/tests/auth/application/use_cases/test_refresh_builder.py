from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from expects import be_a, be_none, equal, expect

from src.auth.application.use_cases.refresh_builder import TenantUserRefreshSessionBuilder
from src.auth.domain.exceptions import InvalidRefreshTokenError
from src.common.application.queries.tenants import GetTenantUserQuery, GetUserTenantQuery
from src.common.application.queries.users import GetUserByIdQuery
from src.common.domain.entities.auth.user_session import TenantUserSession
from src.common.domain.entities.common.jtw_session import JwtSession
from src.common.domain.exceptions.users import UserNotFoundError
from src.common.domain.enums.jwt import JwtTokenScope
from src.common.domain.services.token_builder import JwtTokenClaims


@pytest.fixture
def jwt_claims(user):
    return JwtTokenClaims(
        iss="vnext",
        sub=str(user.uuid),
        iat=1700000000,
        exp=1700003600,
        jti="test-jti-123",
        ns="USER",
        scope=JwtTokenScope.REFRESH,
    )


@pytest.fixture
def refresh_builder(query_bus, token_service):
    return TenantUserRefreshSessionBuilder(
        refresh_token="valid.refresh.token",
        query_bus=query_bus,
        token_service=token_service,
    )


async def test_execute__returns_tenant_user_session(
    refresh_builder, user, jwt_session, jwt_claims, tenant, tenant_user
):
    async def ask_side_effect(query):
        if isinstance(query, GetUserByIdQuery):
            return user
        if isinstance(query, GetUserTenantQuery):
            return tenant
        if isinstance(query, GetTenantUserQuery):
            return tenant_user
        return None

    refresh_builder.query_bus.ask = AsyncMock(side_effect=ask_side_effect)
    refresh_builder.token_service.refresh_token.return_value = (jwt_claims, jwt_session)

    result = await refresh_builder.execute()

    expect(result).to(be_a(TenantUserSession))
    expect(result.session).to(equal(jwt_session))
    expect(result.user).to(equal(user))
    expect(result.tenant).to(equal(tenant))


async def test_execute__empty_refresh_token_raises(query_bus, token_service):
    builder = TenantUserRefreshSessionBuilder(
        refresh_token="",
        query_bus=query_bus,
        token_service=token_service,
    )

    with pytest.raises(InvalidRefreshTokenError):
        await builder.execute()


async def test_execute__none_refresh_token_raises(query_bus, token_service):
    builder = TenantUserRefreshSessionBuilder(
        refresh_token=None,
        query_bus=query_bus,
        token_service=token_service,
    )

    with pytest.raises(InvalidRefreshTokenError):
        await builder.execute()


async def test_execute__user_not_found_raises(refresh_builder, jwt_claims, jwt_session):
    refresh_builder.token_service.refresh_token.return_value = (jwt_claims, jwt_session)
    refresh_builder.query_bus.ask = AsyncMock(return_value=None)

    with pytest.raises(UserNotFoundError):
        await refresh_builder.execute()


async def test_execute__calls_token_service_refresh(
    refresh_builder, user, jwt_session, jwt_claims, tenant, tenant_user
):
    async def ask_side_effect(query):
        if isinstance(query, GetUserByIdQuery):
            return user
        if isinstance(query, GetUserTenantQuery):
            return tenant
        if isinstance(query, GetTenantUserQuery):
            return tenant_user
        return None

    refresh_builder.query_bus.ask = AsyncMock(side_effect=ask_side_effect)
    refresh_builder.token_service.refresh_token.return_value = (jwt_claims, jwt_session)

    await refresh_builder.execute()

    refresh_builder.token_service.refresh_token.assert_called_once_with("valid.refresh.token")


async def test_execute__no_tenant_returns_session_with_none_tenant(refresh_builder, user, jwt_session, jwt_claims):
    async def ask_side_effect(query):
        if isinstance(query, GetUserByIdQuery):
            return user
        if isinstance(query, GetUserTenantQuery):
            return None
        return None

    refresh_builder.query_bus.ask = AsyncMock(side_effect=ask_side_effect)
    refresh_builder.token_service.refresh_token.return_value = (jwt_claims, jwt_session)

    result = await refresh_builder.execute()

    expect(result).to(be_a(TenantUserSession))
    expect(result.tenant).to(be_none)
    expect(result.tenant_role).to(be_none)
