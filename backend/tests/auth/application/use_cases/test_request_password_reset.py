from unittest.mock import AsyncMock, create_autospec

import pytest
from expects import be_a, contain, equal, expect

from src.auth.application.use_cases.request_password_reset import (
    PASSWORD_RESET_TTL,
    RequestPasswordReset,
)
from src.common.application.commands.common import SendEmailCommand
from src.common.domain.buses.commands import CommandBus
from src.common.domain.enums.jwt import JwtTokenScope
from src.users.domain.repositories.user import UserRepository


@pytest.fixture
def user_repository():
    return create_autospec(spec=UserRepository, spec_set=True, instance=True)


@pytest.fixture
def command_bus():
    bus = create_autospec(spec=CommandBus, spec_set=True, instance=True)
    bus.dispatch = AsyncMock(return_value=None)
    return bus


def _make_use_case(
    *,
    email,
    user_repository,
    token_service,
    command_bus,
    reset_base_url="https://app.example.com",
):
    return RequestPasswordReset(
        email=email,
        user_repository=user_repository,
        token_service=token_service,
        command_bus=command_bus,
        reset_base_url=reset_base_url,
    )


async def test_execute__known_user_issues_token_and_dispatches_email(
    user, user_repository, token_service, command_bus
):
    user_repository.find_by_email.return_value = user
    token_service.create_one_shot_token = AsyncMock(
        return_value="reset.jwt.token",  # noqa: S106 — fake test token
    )

    use_case = _make_use_case(
        email="test@example.com",
        user_repository=user_repository,
        token_service=token_service,
        command_bus=command_bus,
    )

    await use_case.execute()

    token_service.create_one_shot_token.assert_called_once()
    call_kwargs = token_service.create_one_shot_token.call_args.kwargs
    expect(call_kwargs["sub"]).to(equal(str(user.uuid)))
    expect(call_kwargs["scope"]).to(equal(JwtTokenScope.PASSWORD_RESET))
    expect(call_kwargs["ttl"]).to(equal(PASSWORD_RESET_TTL))

    command_bus.dispatch.assert_called_once()
    command = command_bus.dispatch.call_args.kwargs["command"]
    expect(command).to(be_a(SendEmailCommand))
    expect(command.to_emails).to(equal(["test@example.com"]))
    expect(command.template_name).to(equal("reset_password"))
    expect(command.context["reset_url"]).to(
        equal("https://app.example.com/reset_password/reset.jwt.token")
    )
    expect(command.context["name"]).to(equal(user.first_name))


async def test_execute__unknown_email_is_silent_noop(
    user_repository, token_service, command_bus
):
    """Security stance: we never reveal whether an email is registered."""
    user_repository.find_by_email.return_value = None
    token_service.create_one_shot_token = AsyncMock()

    use_case = _make_use_case(
        email="ghost@nowhere.com",
        user_repository=user_repository,
        token_service=token_service,
        command_bus=command_bus,
    )

    await use_case.execute()  # Must NOT raise.

    token_service.create_one_shot_token.assert_not_called()
    command_bus.dispatch.assert_not_called()


async def test_execute__normalizes_email_lowercase_and_trimmed(
    user, user_repository, token_service, command_bus
):
    user_repository.find_by_email.return_value = user
    token_service.create_one_shot_token = AsyncMock(
        return_value="t",  # noqa: S106 — fake test token
    )

    use_case = _make_use_case(
        email="  Test@Example.COM  ",
        user_repository=user_repository,
        token_service=token_service,
        command_bus=command_bus,
    )

    await use_case.execute()

    user_repository.find_by_email.assert_called_once_with("test@example.com")
    command = command_bus.dispatch.call_args.kwargs["command"]
    expect(command.to_emails).to(equal(["test@example.com"]))


async def test_execute__strips_trailing_slash_from_reset_base_url(
    user, user_repository, token_service, command_bus
):
    user_repository.find_by_email.return_value = user
    token_service.create_one_shot_token = AsyncMock(
        return_value="t",  # noqa: S106 — fake test token
    )

    use_case = _make_use_case(
        email="test@example.com",
        user_repository=user_repository,
        token_service=token_service,
        command_bus=command_bus,
        reset_base_url="https://app.example.com/",
    )

    await use_case.execute()

    command = command_bus.dispatch.call_args.kwargs["command"]
    expect(command.context["reset_url"]).to(
        contain("https://app.example.com/reset_password/")
    )
