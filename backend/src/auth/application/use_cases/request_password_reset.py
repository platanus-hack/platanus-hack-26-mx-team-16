"""Issue a password-reset token and email it to the user.

Security stance: we **always** resolve successfully, regardless of
whether the email maps to a real user. This avoids leaking which emails
are registered in the system. If the lookup misses, no email is sent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from src.common.application.commands.common import SendEmailCommand
from src.common.domain.buses.commands import CommandBus
from src.common.domain.enums.jwt import JwtTokenScope
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.services.token_service import TokenService
from src.common.settings import settings
from src.users.domain.repositories.user import UserRepository

PASSWORD_RESET_TTL = timedelta(hours=1)


@dataclass
class RequestPasswordReset(UseCase):
    email: str
    user_repository: UserRepository
    token_service: TokenService
    command_bus: CommandBus
    reset_base_url: str = field(
        default_factory=lambda: settings.FRONTEND_HOST or "http://localhost:3000"
    )

    async def execute(self) -> None:
        normalized = self.email.strip().lower()
        user = await self.user_repository.find_by_email(normalized)
        if user is None:
            # Silent success: don't leak that the email is unknown.
            return

        token = await self.token_service.create_one_shot_token(
            sub=str(user.uuid),
            scope=JwtTokenScope.PASSWORD_RESET,
            ttl=PASSWORD_RESET_TTL,
        )
        reset_url = (
            f"{self.reset_base_url.rstrip('/')}/reset_password/{token}"
        )
        await self.command_bus.dispatch(
            command=SendEmailCommand(
                to_emails=[normalized],
                subject="Restablece tu contraseña",
                template_name="reset_password",
                context={
                    "name": user.first_name or normalized,
                    "reset_url": reset_url,
                },
            ),
        )
