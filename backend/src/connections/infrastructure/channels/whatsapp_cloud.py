"""WhatsApp Cloud API (Meta) channel adapter (E6 · W5 · diseño §5).

Meta POSTs ``entry[].changes[].value`` JSON signed with
``X-Hub-Signature-256: sha256=<hex HMAC(app_secret, raw_body)>``. Media is not
inline: each non-text message carries a ``media_id`` resolved via
``GET {graph}/{media_id}`` (Bearer access token) to an ephemeral URL (~5 min),
then downloaded with the same Bearer. That two-step download runs in a
background task AFTER the 200 ACK (the endpoint owns the deferral).

Credentials live on the Source so :meth:`verify`/:meth:`fetch_attachment` are
self-contained:
- ``source.secret``            → the Meta access token (Bearer).
- ``source.config["app_secret"]``       → HMAC key for the signature.
- ``source.config["verify_token"]``     → GET ``hub.challenge`` echo token.
- ``source.config["phone_number_id"]``  → expected ``value.metadata.phone_number_id``.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from src.common.application.logging import get_logger
from src.common.settings import settings
from src.connections.domain.channels.base import ChannelAdapter, ChannelRequest
from src.connections.domain.models.channel_message import ChannelAttachment, ChannelMessage
from src.connections.domain.models.workflow_source import WorkflowSource
from src.connections.domain.services.channel_auth import verify_meta_signature

logger = get_logger(__name__)

VENDOR = "whatsapp_cloud"
_FETCH_TIMEOUT = 20.0

# Default WhatsApp filename per message type when the provider omits one.
_DEFAULT_EXT = {
    "audio": "ogg",
    "image": "jpg",
    "video": "mp4",
    "document": "bin",
}


class WhatsappCloudChannelAdapter(ChannelAdapter):
    def verify(self, source: WorkflowSource, request: ChannelRequest) -> bool:
        return verify_meta_signature(
            app_secret=str(source.config.get("app_secret") or ""),
            raw_body=request.raw_body,
            header_value=request.header("X-Hub-Signature-256"),
        )

    def parse(self, source: WorkflowSource, request: ChannelRequest) -> list[ChannelMessage]:
        import json

        try:
            payload = json.loads(request.raw_body or b"{}")
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, dict):
            return []

        messages: list[ChannelMessage] = []
        for entry in payload.get("entry") or []:
            for change in (entry or {}).get("changes") or []:
                value = (change or {}).get("value") or {}
                metadata = value.get("metadata") or {}
                phone_number_id = str(metadata.get("phone_number_id") or "")
                for msg in value.get("messages") or []:
                    parsed = self._parse_message(msg, phone_number_id)
                    if parsed is not None:
                        messages.append(parsed)
        return messages

    def _parse_message(self, msg: dict, phone_number_id: str) -> ChannelMessage | None:
        wamid = str(msg.get("id") or "")
        if not wamid:
            return None
        msg_type = str(msg.get("type") or "")
        sender = str(msg.get("from") or "")
        context = msg.get("context") or {}
        thread_ref = str(context.get("id") or "") or None

        text: str | None = None
        attachments: list[ChannelAttachment] = []

        if msg_type == "text":
            text = str((msg.get("text") or {}).get("body") or "") or None
        elif msg_type in _DEFAULT_EXT:
            media = msg.get(msg_type) or {}
            media_id = str(media.get("id") or "")
            text = str(media.get("caption") or "") or None
            if media_id:
                filename = str(media.get("filename") or "")
                if not filename:
                    filename = f"{msg_type}-{wamid[-12:]}.{_DEFAULT_EXT[msg_type]}"
                attachments.append(
                    ChannelAttachment(
                        filename=filename,
                        content_type=str(media.get("mime_type") or "application/octet-stream"),
                        fetch_ref=media_id,
                    )
                )

        return ChannelMessage(
            provider="whatsapp",
            provider_message_id=wamid,
            sender=sender,
            recipient=phone_number_id,
            received_at=datetime.now(UTC),
            subject=None,
            text=text,
            attachments=attachments,
            thread_ref=thread_ref,
        )

    async def fetch_attachment(self, source: WorkflowSource, ref: str) -> tuple[bytes, str]:
        access_token = source.secret or ""
        if not access_token:
            raise RuntimeError("WhatsApp source has no access token")
        graph = f"https://graph.facebook.com/{settings.META_GRAPH_API_VERSION}"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
            # Step 1: media_id → ephemeral URL.
            meta_resp = await client.get(f"{graph}/{ref}", headers=headers)
            meta_resp.raise_for_status()
            media = meta_resp.json()
            media_url = str(media.get("url") or "")
            content_type = str(media.get("mime_type") or "application/octet-stream")
            if not media_url:
                raise RuntimeError("WhatsApp media lookup returned no url")
            # Step 2: download the bytes with the same Bearer.
            file_resp = await client.get(media_url, headers=headers)
            file_resp.raise_for_status()
            resolved_type = (file_resp.headers.get("content-type") or "").split(";")[0].strip()
            return file_resp.content, (resolved_type or content_type)

    def hub_challenge(self, source: WorkflowSource, query: dict[str, str]) -> str | None:
        """Return ``hub.challenge`` iff ``hub.verify_token`` matches the source config."""
        if query.get("hub.mode") != "subscribe":
            return None
        expected = str(source.config.get("verify_token") or "")
        if expected and query.get("hub.verify_token") == expected:
            return query.get("hub.challenge")
        return None
