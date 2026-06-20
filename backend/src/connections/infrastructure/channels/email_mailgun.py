"""Mailgun Routes email channel adapter (E6 · W5 · diseño §5).

Mailgun POSTs ``multipart/form-data`` with the parsed message fields plus
``attachment-count`` + ``attachment-1..N`` file parts. The request is signed
with ``signature = hex HMAC_SHA256(signing_key, timestamp+token)``; the signing
key is the Source's secret (``source.secret``).
"""

from __future__ import annotations

from datetime import UTC, datetime

from src.connections.domain.channels.base import ChannelAdapter, ChannelRequest
from src.connections.domain.models.channel_message import ChannelAttachment, ChannelMessage
from src.connections.domain.models.workflow_source import WorkflowSource
from src.connections.domain.services.channel_auth import verify_mailgun_signature

VENDOR = "mailgun"


class MailgunChannelAdapter(ChannelAdapter):
    def verify(self, source: WorkflowSource, request: ChannelRequest) -> bool:
        return verify_mailgun_signature(
            signing_key=source.secret or "",
            timestamp=request.form.get("timestamp"),
            token=request.form.get("token"),
            signature=request.form.get("signature"),
        )

    def parse(self, source: WorkflowSource, request: ChannelRequest) -> list[ChannelMessage]:
        form = request.form
        message_id = (form.get("Message-Id") or form.get("message-id") or "").strip()
        if not message_id:
            return []

        attachments: list[ChannelAttachment] = []
        for field_name, (filename, content_type, content) in request.files.items():
            if not field_name.lower().startswith("attachment"):
                continue
            attachments.append(
                ChannelAttachment(
                    filename=filename or "attachment",
                    content_type=content_type or "application/octet-stream",
                    content=content,
                )
            )

        return [
            ChannelMessage(
                provider="email",
                provider_message_id=message_id,
                sender=(form.get("sender") or form.get("from") or "").strip(),
                recipient=(form.get("recipient") or form.get("to") or "").strip(),
                received_at=datetime.now(UTC),
                subject=(form.get("subject") or "").strip() or None,
                text=(form.get("body-plain") or form.get("stripped-text") or "").strip() or None,
                attachments=attachments,
                thread_ref=(form.get("In-Reply-To") or form.get("References") or "").strip()
                or None,
            )
        ]
