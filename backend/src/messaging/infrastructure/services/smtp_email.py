import asyncio
from dataclasses import dataclass
from email.message import EmailMessage

import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from config import EMAIL_TEMPLATES_PATH
from src.common.application.logging import get_logger

logger = get_logger(__name__)
from src.common.constants import MAX_CONCURRENT_EMAILS
from src.messaging.domain.services.email import EmailService


@dataclass
class SmtpEmailService(EmailService):
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_tls: bool
    templates_dir: str | None = EMAIL_TEMPLATES_PATH
    templates_env: Environment | None = None
    max_concurrent_emails: int = MAX_CONCURRENT_EMAILS

    def __post_init__(self):
        self.templates_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=True,
        )

    async def send_email(
        self,
        subject: str,
        sender: str,
        recipients: list[str],
        template_name: str,
        context: dict[str, str] | None = None,
    ) -> None:
        context = context or {}

        html_template = self.templates_env.get_template(
            name=f"{template_name}/message.html",
        )
        text_template = self.templates_env.get_template(
            name=f"{template_name}/message.txt",
        )
        subject_template = self.templates_env.get_template(
            name=f"{template_name}/subject.txt",
        )

        subject_content = subject_template.render(**context)
        text_content = text_template.render(**context)
        html_content = html_template.render(**context)

        semaphore = asyncio.Semaphore(self.max_concurrent_emails)

        async def send_single_email(to_email: str) -> None:
            async with semaphore:
                message = EmailMessage()
                message["From"] = sender
                message["To"] = to_email
                message["Subject"] = subject or subject_content
                message.set_content(text_content)
                message.add_alternative(html_content, subtype="html")

                try:
                    await aiosmtplib.send(
                        message,
                        hostname=self.smtp_host,
                        port=self.smtp_port,
                        username=self.smtp_username,
                        password=self.smtp_password,
                        start_tls=self.smtp_tls,
                    )
                    logger.info(
                        "email.sent",
                        recipient=to_email,
                        template=template_name,
                        subject=subject or subject_content,
                    )
                except Exception as e:
                    logger.error(
                        "email.send_failed",
                        recipient=to_email,
                        template=template_name,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise

        tasks = [send_single_email(to_email) for to_email in recipients]
        await asyncio.gather(*tasks)
