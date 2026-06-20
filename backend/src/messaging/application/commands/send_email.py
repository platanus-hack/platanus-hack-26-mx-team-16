from dataclasses import dataclass

from src.common.application.commands.common import SendEmailCommand
from src.common.domain.buses.commands import CommandHandler
from src.common.settings import settings
from src.messaging.domain.services.email import EmailService


@dataclass
class SendEmailHandler(CommandHandler[SendEmailCommand]):
    email_service: EmailService

    async def execute(self, command: SendEmailCommand):
        await self.email_service.send_email(
            subject=command.subject,
            sender=command.from_email or settings.DEFAULT_FROM_EMAIL,
            recipients=command.to_emails,
            template_name=command.template_name,
            context=command.context or {},
        )
