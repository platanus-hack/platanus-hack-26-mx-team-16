from src.common.application.commands.common import ExampleJobCommand, SendEmailCommand
from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.common.settings import settings
from src.messaging.application.commands.example_job import ExampleJobHandler
from src.messaging.application.commands.send_email import SendEmailHandler
from src.messaging.infrastructure.services.smtp_email import SmtpEmailService

email_service = SmtpEmailService(
    smtp_host=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    smtp_username=settings.SMTP_USERNAME,
    smtp_password=settings.SMTP_PASSWORD,
    smtp_tls=settings.SMTP_TLS,
)


def messaging_wiring(
    _domain: DomainContext,
    bus: BusContext,
):
    #  C O M M A N D S
    bus.command_bus.subscribe(
        command=SendEmailCommand,
        handler=SendEmailHandler(
            email_service=email_service,
        ),
    )
    # Reference background job (boilerplate D3) — copy this for new async jobs.
    bus.command_bus.subscribe(
        command=ExampleJobCommand,
        handler=ExampleJobHandler(),
    )

    #  Q U E R I E S
