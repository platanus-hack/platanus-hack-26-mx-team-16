"""Provider-agnostic channel adapter contract (E6 · W5 · diseño §5).

A channel adapter turns one provider's inbound webhook into the normalized
:class:`ChannelMessage` contract and verifies that the request really came from
that provider. The push model (the provider calls us) replaces the F12 polling
scaffolds (`EmailSourceAdapter.poll` / `WhatsappSourceAdapter.poll`).

Adapters are intentionally framework-light: they receive a plain
:class:`ChannelRequest` (raw body + headers + query + parsed form) so the same
adapter can be unit-tested without FastAPI. Concrete adapters live in
``infrastructure/channels/``; the registry maps a provider key to an instance.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.connections.domain.models.channel_message import ChannelMessage
from src.connections.domain.models.workflow_source import WorkflowSource


@dataclass
class ChannelRequest:
    """Everything an adapter needs from the inbound HTTP request.

    ``raw_body`` is the exact bytes received (required for HMAC over the raw
    body, e.g. Meta's ``X-Hub-Signature-256``). ``form`` holds multipart fields
    for providers that post ``multipart/form-data`` (Mailgun). ``files`` maps a
    field name to ``(filename, content_type, bytes)`` for multipart attachments.
    """

    raw_body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    query: dict[str, str] = field(default_factory=dict)
    form: dict[str, str] = field(default_factory=dict)
    files: dict[str, tuple[str, str, bytes]] = field(default_factory=dict)

    def header(self, name: str) -> str | None:
        """Case-insensitive header lookup."""
        target = name.lower()
        for key, value in self.headers.items():
            if key.lower() == target:
                return value
        return None


class ChannelAdapter(ABC):
    """Bridges one provider's webhook to the normalized channel contract."""

    @abstractmethod
    def verify(self, source: WorkflowSource, request: ChannelRequest) -> bool:
        """Return ``True`` when the request's signature proves the provider sent it.

        The credential lives on the Source (``source.secret``) or its linked
        account/config — NOT the Svix-style ``auth_mode`` of the API ingest
        endpoint. Adapters without a signature scheme (mailpit, dev) return
        ``True`` unconditionally.
        """
        raise NotImplementedError

    @abstractmethod
    def parse(self, source: WorkflowSource, request: ChannelRequest) -> list[ChannelMessage]:
        """Parse the verified payload into zero or more channel messages."""
        raise NotImplementedError

    async def fetch_attachment(
        self, source: WorkflowSource, ref: str
    ) -> tuple[bytes, str]:
        """Resolve a deferred attachment handle to ``(bytes, content_type)``.

        Default raises: only providers that defer media (WhatsApp ``media_id``,
        mailpit message ID) override this.
        """
        raise NotImplementedError("This channel adapter has no deferred media to fetch.")
