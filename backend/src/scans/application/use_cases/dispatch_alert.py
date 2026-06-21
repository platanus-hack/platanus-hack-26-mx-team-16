"""``DispatchAlert`` — send a redacted monitoring alert over the channels the
owner enabled, and log each delivery (08-ranking-watchlists §5.1).

Channels (read from ``notification_prefs``, account-level):
- **Email (Resend):** if ``email_enabled`` — dispatched via the existing
  command bus (``SendEmailCommand`` → ``SendEmailHandler`` → ``EmailService``),
  reusing ``DEFAULT_FROM_EMAIL`` as the sender.
- **Slack:** if ``slack_webhook_url`` is set — a plain JSON POST via
  ``post_slack_alert`` (never the signed ``deliver_webhook``).

Every successful or attempted delivery is recorded in ``alerts`` via
``AlertRepository.log``. A site without an owner (gov seed) has no recipient, so
the caller never invokes this for it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from uuid import UUID

from src.common.application.commands.common import SendEmailCommand
from src.common.application.logging import get_logger
from src.common.domain.buses.commands import CommandBus
from src.common.domain.enums.scans import AlertChannel
from src.common.domain.interfaces.use_case import UseCase
from src.scans.domain.models.alert import Alert
from src.scans.domain.repositories.alert import AlertRepository
from src.scans.infrastructure.alerts.render import AlertPayload
from src.scans.infrastructure.services.slack_alert import post_slack_alert
from src.sites.domain.models.notification_prefs import NotificationPrefs

logger = get_logger(__name__)

_ALERT_EMAIL_TEMPLATE = "monitoring_alert"


@dataclass
class DispatchAlert(UseCase):
    user_id: UUID
    site_id: UUID
    scan_id: UUID | None
    recipient_email: str | None
    prefs: NotificationPrefs
    payload: AlertPayload
    alert_repository: AlertRepository
    command_bus: CommandBus

    async def execute(self, *args, **kwargs) -> list[Alert]:
        logged: list[Alert] = []

        # -> EMAIL (Resend via command bus). Sender defaults to DEFAULT_FROM_EMAIL.
        if self.prefs.email_enabled and self.recipient_email:
            await self.command_bus.dispatch(
                SendEmailCommand(
                    to_emails=[self.recipient_email],
                    template_name=_ALERT_EMAIL_TEMPLATE,
                    subject=self.payload.subject,
                    context={
                        "body": self.payload.as_text(),
                        **self.payload.to_dict,
                    },
                ),
                run_async=False,
            )
            logged.append(
                await self._log(AlertChannel.EMAIL),
            )

        # -> SLACK (plain incoming webhook). Never raises.
        if self.prefs.slack_webhook_url:
            result = await post_slack_alert(
                webhook_url=self.prefs.slack_webhook_url,
                payload=self.payload,
            )
            if not result.delivered:
                logger.info(
                    "alert.slack_delivery_failed",
                    site_id=str(self.site_id),
                    status_code=result.status_code,
                    error=result.error,
                )
            logged.append(await self._log(AlertChannel.SLACK))

        return logged

    async def _log(self, channel: AlertChannel) -> Alert:
        alert_type = "grade_drop" if self.payload.grade_dropped else "new_critical"
        return await self.alert_repository.log(
            Alert(
                uuid=uuid.uuid4(),
                user_id=self.user_id,
                site_id=self.site_id,
                scan_id=self.scan_id,
                type=alert_type,
                message=self.payload.summary_line,
                channel=str(channel),
            )
        )
