"""Provider-agnostic inbound channel message contract (E6 · W5 · diseño §5).

A :class:`ChannelMessage` is the normalized shape every channel adapter (email,
WhatsApp, …) produces from a provider-specific webhook payload. The channel
endpoint (`POST /v1/channels/{provider}/{route_token}`) consumes only this
contract: it dedups by ``provider_message_id``, resolves a case by the source's
``case_strategy``, uploads each attachment bytes-first, and dispatches the
shared ingest pipeline. Keeping it a plain dataclass (not pydantic) matches the
design and keeps adapters free of validation coupling — the adapter is the only
thing that knows the wire shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ChannelAttachment:
    """One file carried by an inbound channel message.

    ``content`` is the inline bytes (multipart/base64/MIME parse). ``fetch_ref``
    is a provider handle (Meta ``media_id``, mailpit message ID) for media that
    must be downloaded out-of-band; the adapter resolves it to bytes via
    ``fetch_attachment``. Exactly one of the two is expected to be set by the
    time the file is uploaded.
    """

    filename: str
    content_type: str
    content: bytes | None = None
    fetch_ref: str | None = None


@dataclass
class ChannelMessage:
    """Normalized inbound message, provider-agnostic (diseño §5)."""

    provider: str  # "email" | "whatsapp" — matches WorkflowSource.provider
    provider_message_id: str  # Message-ID | wamid — the dedup idempotency key
    sender: str  # from address | wa_id
    recipient: str  # rcpt / mailbox | phone_number_id
    received_at: datetime
    subject: str | None = None  # email only
    text: str | None = None  # body / caption
    attachments: list[ChannelAttachment] = field(default_factory=list)
    thread_ref: str | None = None  # In-Reply-To/References | context.id
