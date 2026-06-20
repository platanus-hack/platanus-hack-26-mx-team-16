from unittest.mock import AsyncMock, create_autospec
from uuid import uuid4

import pytest
from expects import equal, expect

from src.auth.application.use_cases.reset_password_with_token import (
    ResetPasswordWithToken,
)
from src.common.domain.enums.jwt import JwtTokenScope
from src.common.domain.exceptions.common import InvalidOrExpiredTokenError
from src.common.domain.services.token_builder import JwtTokenClaims
from src.users.domain.repositories.user import UserRepository


@pytest.fixture
def user_repository():
    return create_autospec(spec=UserRepository, spec_set=True, instance=True)


def _valid_claims(user_id):
    return JwtTokenClaims(
        iss="vnext",
        sub=str(user_id),
        iat=1700000000,
        exp=1700003600,
        jti="test-jti",
        ns="JWT",
        scope=JwtTokenScope.PASSWORD_RESET,
    )


async def test_execute__valid_token_sets_password(user_repository, token_service):
    user_id = uuid4()
    token_service.get_claims = AsyncMock(return_value=_valid_claims(user_id))
    user_repository.set_password.return_value = True

    use_case = ResetPasswordWithToken(
        token="valid.token",  # noqa: S106 — fake test token
        new_password="newSecret123",  # noqa: S106 — fake test password
        user_repository=user_repository,
        token_service=token_service,
    )

    await use_case.execute()

    user_repository.set_password.assert_called_once()
    call_kwargs = user_repository.set_password.call_args.kwargs
    expect(call_kwargs["user_id"]).to(equal(user_id))
    expect(call_kwargs["new_password"]).to(equal("newSecret123"))
    token_service.get_claims.assert_called_once_with(
        "valid.token",
        scope=JwtTokenScope.PASSWORD_RESET,
    )


async def test_execute__invalid_token_raises(user_repository, token_service):
    token_service.get_claims = AsyncMock(return_value=None)

    use_case = ResetPasswordWithToken(
        token="bad.token",  # noqa: S106 — fake test token
        new_password="newSecret123",  # noqa: S106 — fake test password
        user_repository=user_repository,
        token_service=token_service,
    )

    with pytest.raises(InvalidOrExpiredTokenError):
        await use_case.execute()

    user_repository.set_password.assert_not_called()


async def test_execute__malformed_sub_raises(user_repository, token_service):
    bogus = JwtTokenClaims(
        iss="vnext",
        sub="not-a-uuid",
        iat=1700000000,
        exp=1700003600,
        jti="t",
        ns="JWT",
        scope=JwtTokenScope.PASSWORD_RESET,
    )
    token_service.get_claims = AsyncMock(return_value=bogus)

    use_case = ResetPasswordWithToken(
        token="t",  # noqa: S106 — fake test token
        new_password="newSecret123",  # noqa: S106 — fake test password
        user_repository=user_repository,
        token_service=token_service,
    )

    with pytest.raises(InvalidOrExpiredTokenError):
        await use_case.execute()


async def test_execute__user_disappeared_raises(user_repository, token_service):
    """Defensive: if the user was removed between issuing and consuming
    the token, set_password returns False — we surface it as
    invalid/expired rather than crashing."""
    user_id = uuid4()
    token_service.get_claims = AsyncMock(return_value=_valid_claims(user_id))
    user_repository.set_password.return_value = False

    use_case = ResetPasswordWithToken(
        token="t",  # noqa: S106 — fake test token
        new_password="newSecret123",  # noqa: S106 — fake test password
        user_repository=user_repository,
        token_service=token_service,
    )

    with pytest.raises(InvalidOrExpiredTokenError):
        await use_case.execute()
