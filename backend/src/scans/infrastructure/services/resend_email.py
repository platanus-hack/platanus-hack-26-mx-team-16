"""Resend transactional-email implementation of ``EmailService``
(08-ranking-watchlists §5.1/§5.4).

A second ``EmailService`` impl (alongside ``SmtpEmailService``) that posts to the
Resend HTTP API via ``httpx``. The sender is whatever the command bus passes —
which is ``DEFAULT_FROM_EMAIL`` (we deliberately do **not** add a ``RESEND_FROM``
setting; the verified sender is configured there). If ``RESEND_API_KEY`` is not
set the service **degrades gracefully** (logs and returns) rather than breaking
the monitoring cycle.

The ``resend`` SDK is intentionally avoided; a plain ``httpx`` POST keeps imports
light and lets tests mock HTTP. ``httpx`` is already a backend dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from src.common.application.logging import get_logger
from src.messaging.domain.services.email import EmailService

logger = get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
_DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass
class ResendEmailService(EmailService):
    api_key: str | None = None
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS

    async def send_email(
        self,
        subject: str,
        sender: str,
        recipients: list[str],
        template_name: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        if not self.api_key:
            # No Resend key configured: degrade — do not raise (§5.4). The
            # monitoring cycle must keep running even without an email channel.
            logger.info(
                "resend.skipped_no_api_key",
                template=template_name,
                recipients=recipients,
            )
            return

        context = context or {}
        # The redacted alert text is passed in the context (no templates dir on
        # the worker for Resend); fall back to subject if absent.
        body_text = str(context.get("body", subject))
        html_body = str(context.get("html", f"<pre>{body_text}</pre>"))

        payload = {
            "from": sender,
            "to": recipients,
            "subject": subject,
            "text": body_text,
            "html": html_body,
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    RESEND_API_URL, json=payload, headers=headers
                )
            response.raise_for_status()
            logger.info("resend.sent", template=template_name, recipients=recipients)
        except httpx.HTTPError as exc:
            # Degrade — log and swallow so a transient Resend outage never
            # poisons the monitoring run (§5.4 fire-and-forget posture).
            logger.error(
                "resend.send_failed",
                template=template_name,
                error=str(exc),
                error_type=type(exc).__name__,
            )
