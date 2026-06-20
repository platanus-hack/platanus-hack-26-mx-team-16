"""Mailpit email channel adapter — dev/E2E only (E6 · W5 · diseño §5).

Mirror of the E3 "VLM dev" pattern: mailpit (in docker-compose) accepts inbound
SMTP and, with ``MP_WEBHOOK_URL`` set, POSTs a small JSON envelope to the backend
for each received message. The envelope has an ``ID``; the full message and its
attachments are read back from mailpit's HTTP API
(``GET {MAILPIT_API_URL}/api/v1/message/{ID}``), then each attachment's bytes
from ``.../part/{PartID}``.

No signature: mailpit runs on the local docker network only, so :meth:`verify`
returns ``True``. Never enable this adapter in production.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx

from src.common.application.logging import get_logger
from src.common.settings import settings
from src.connections.domain.channels.base import ChannelAdapter, ChannelRequest
from src.connections.domain.models.channel_message import ChannelAttachment, ChannelMessage
from src.connections.domain.models.workflow_source import WorkflowSource

logger = get_logger(__name__)

VENDOR = "mailpit"
_FETCH_TIMEOUT = 20.0


class MailpitChannelAdapter(ChannelAdapter):
    def verify(self, source: WorkflowSource, request: ChannelRequest) -> bool:
        # Dev-only, local docker network — no signature scheme. The public
        # endpoint trusts this return value, and the route_token is published in
        # the inbound alias (not a secret), so an unconditional True in
        # production would accept forged, unsigned webhooks. Hard-fail in prod
        # regardless of how the source was configured (defense in depth).
        if settings.ENVIRONMENT.is_production:
            return False
        return True

    def parse(self, source: WorkflowSource, request: ChannelRequest) -> list[ChannelMessage]:
        try:
            payload = json.loads(request.raw_body or b"{}")
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, dict):
            return []

        message_id = str(payload.get("MessageID") or payload.get("ID") or "")
        if not message_id:
            return []
        mailpit_id = str(payload.get("ID") or "")

        from_field = payload.get("From") or {}
        sender = str(from_field.get("Address") if isinstance(from_field, dict) else from_field or "")
        to_list = payload.get("To") or []
        recipient = ""
        if isinstance(to_list, list) and to_list:
            first = to_list[0]
            recipient = str(first.get("Address") if isinstance(first, dict) else first or "")

        # Defer attachment bytes to fetch_attachment (read from mailpit's API),
        # keyed by the mailpit message ID + part id. The message-list webhook
        # envelope does not carry attachment bytes.
        attachments: list[ChannelAttachment] = []
        for att in payload.get("Attachments") or []:
            if not isinstance(att, dict):
                continue
            part_id = str(att.get("PartID") or "")
            attachments.append(
                ChannelAttachment(
                    filename=str(att.get("FileName") or att.get("filename") or "attachment"),
                    content_type=str(att.get("ContentType") or "application/octet-stream"),
                    fetch_ref=f"{mailpit_id}:{part_id}" if mailpit_id else None,
                )
            )

        return [
            ChannelMessage(
                provider="email",
                provider_message_id=message_id,
                sender=sender,
                recipient=recipient,
                received_at=datetime.now(UTC),
                subject=str(payload.get("Subject") or "") or None,
                text=str(payload.get("Text") or payload.get("Snippet") or "") or None,
                attachments=attachments,
                thread_ref=None,
            )
        ]

    async def fetch_attachment(self, source: WorkflowSource, ref: str) -> tuple[bytes, str]:
        base = (settings.MAILPIT_API_URL or "").rstrip("/")
        if not base:
            raise RuntimeError("MAILPIT_API_URL is not configured")
        mailpit_id, _, part_id = ref.partition(":")
        url = f"{base}/api/v1/message/{mailpit_id}/part/{part_id}"
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = (response.headers.get("content-type") or "").split(";")[0].strip()
            return response.content, content_type or "application/octet-stream"
