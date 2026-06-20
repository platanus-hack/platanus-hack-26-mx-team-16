"""E5 · ADR 0001 — identidad staff en el payload de sesión.

El FE gatea la consola `/staff` con `user.isStaff` (+ `staffRole` para la
vista de audit): login, google y refresh deben exponerlos; el presenter los
serializa dentro de `user`.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from expects import be_false, be_none, be_true, equal, expect

from src.auth.application.use_cases.refresh_builder import TenantUserRefreshSessionBuilder
from src.auth.application.use_cases.session_builder import TenantUserSessionBuilder
from src.auth.presentation.presenters.session import TenantUserSessionPresenter
from src.common.application.queries.tenants import GetTenantUserQuery, GetUserTenantQuery
from src.common.application.queries.users import CheckPasswordQuery, GetUserByEmailQuery, GetUserByIdQuery
from src.common.domain.entities.auth.user_session import TenantUserSession
from src.staff.domain.models.staff_user import StaffRole, StaffUser, StaffUserStatus


@pytest.fixture
def staff_user(user):
    return StaffUser(
        uuid=uuid4(),
        user_id=user.uuid,
        role=StaffRole.STAFF_ADMIN,
        status=StaffUserStatus.ACTIVE,
    )


@pytest.fixture
def staff_repository(staff_user):
    repo = AsyncMock()
    repo.find_active_by_user_id = AsyncMock(return_value=staff_user)
    return repo


def _login_side_effect(user, tenant, tenant_user):
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

    return ask_side_effect


async def test_login__active_staff_row_sets_is_staff_and_role(
    query_bus, token_service, user, jwt_session, tenant, tenant_user, staff_repository
):
    query_bus.ask = AsyncMock(side_effect=_login_side_effect(user, tenant, tenant_user))
    token_service.generate_token.return_value = jwt_session

    result = await TenantUserSessionBuilder(
        email="test@example.com",
        password="password123",
        query_bus=query_bus,
        token_service=token_service,
        staff_user_repository=staff_repository,
    ).execute()

    expect(result.is_staff).to(be_true)
    expect(result.staff_role).to(equal("staff_admin"))
    token_service.generate_token.assert_called_once_with(
        sub=str(user.uuid),
        namespace="USER",
        extra_claims={"is_staff": True},
    )


async def test_login__no_staff_row_defaults_false(
    query_bus, token_service, user, jwt_session, tenant, tenant_user, staff_repository
):
    staff_repository.find_active_by_user_id.return_value = None
    query_bus.ask = AsyncMock(side_effect=_login_side_effect(user, tenant, tenant_user))
    token_service.generate_token.return_value = jwt_session

    result = await TenantUserSessionBuilder(
        email="test@example.com",
        password="password123",
        query_bus=query_bus,
        token_service=token_service,
        staff_user_repository=staff_repository,
    ).execute()

    expect(result.is_staff).to(be_false)
    expect(result.staff_role).to(be_none)


async def test_refresh__re_derives_is_staff_from_active_row(
    query_bus, token_service, user, jwt_session, tenant, tenant_user, staff_repository
):
    async def ask_side_effect(query):
        if isinstance(query, GetUserByIdQuery):
            return user
        if isinstance(query, GetUserTenantQuery):
            return tenant
        if isinstance(query, GetTenantUserQuery):
            return tenant_user
        return None

    query_bus.ask = AsyncMock(side_effect=ask_side_effect)
    token_service.refresh_token.return_value = (
        SimpleNamespace(sub=str(user.uuid)),
        jwt_session,
    )

    result = await TenantUserRefreshSessionBuilder(
        refresh_token="refresh.token.here",
        query_bus=query_bus,
        token_service=token_service,
        staff_user_repository=staff_repository,
    ).execute()

    expect(result.is_staff).to(be_true)
    expect(result.staff_role).to(equal("staff_admin"))


async def test_presenter__exposes_is_staff_and_staff_role_in_user_dict(user, jwt_session, tenant):
    session = TenantUserSession(
        session=jwt_session,
        user=user,
        tenant=tenant,
        is_staff=True,
        staff_role="staff_analyst_l1",
    )

    payload = TenantUserSessionPresenter(session).to_dict

    expect(payload["user"]["is_staff"]).to(be_true)
    expect(payload["user"]["staff_role"]).to(equal("staff_analyst_l1"))


async def test_presenter__defaults_false_without_staff_identity(user, jwt_session, tenant):
    session = TenantUserSession(session=jwt_session, user=user, tenant=tenant)

    payload = TenantUserSessionPresenter(session).to_dict

    expect(payload["user"]["is_staff"]).to(be_false)
    expect(payload["user"]["staff_role"]).to(be_none)
