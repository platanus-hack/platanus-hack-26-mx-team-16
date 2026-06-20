"""E6 · W5: channel adapters — parse + verify (mailpit, mailgun, whatsapp)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from uuid import uuid4

from expects import be_none, equal, expect

from src.common.domain.enums.connections import ConnectionProvider
from src.connections.domain.channels.base import ChannelRequest
from src.connections.domain.models.workflow_source import WorkflowSource
from src.connections.infrastructure.channels.email_mailgun import MailgunChannelAdapter
from src.connections.infrastructure.channels.email_mailpit import MailpitChannelAdapter
from src.connections.infrastructure.channels.registry import (
    get_channel_adapter,
    resolve_vendor,
)
from src.connections.infrastructure.channels.whatsapp_cloud import (
    WhatsappCloudChannelAdapter,
)


def _source(provider: ConnectionProvider, *, secret=None, config=None) -> WorkflowSource:
    return WorkflowSource(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        provider=provider,
        route_token="src_abc",
        secret=secret,
        config=config or {},
    )


# ── mailpit (dev, no signature) ──────────────────────────────────────────────
def test_mailpit__parses_envelope_and_defers_attachment():
    adapter = MailpitChannelAdapter()
    source = _source(ConnectionProvider.EMAIL)
    payload = {
        "ID": "mp-1",
        "MessageID": "<order-1@helados>",
        "From": {"Address": "cliente@x.com"},
        "To": [{"Address": "in+src_abc@doxiq.dev"}],
        "Subject": "Pedido",
        "Text": "Quiero 3 cajas",
        "Attachments": [{"PartID": "2", "FileName": "pedido.pdf", "ContentType": "application/pdf"}],
    }
    ctx = ChannelRequest(raw_body=json.dumps(payload).encode())

    expect(adapter.verify(source, ctx)).to(equal(True))
    messages = adapter.parse(source, ctx)

    expect(len(messages)).to(equal(1))
    msg = messages[0]
    expect(msg.provider).to(equal("email"))
    expect(msg.provider_message_id).to(equal("<order-1@helados>"))
    expect(msg.sender).to(equal("cliente@x.com"))
    expect(msg.text).to(equal("Quiero 3 cajas"))
    expect(len(msg.attachments)).to(equal(1))
    expect(msg.attachments[0].fetch_ref).to(equal("mp-1:2"))
    expect(msg.attachments[0].content).to(be_none)


def test_mailpit__empty_body_yields_no_messages():
    adapter = MailpitChannelAdapter()
    source = _source(ConnectionProvider.EMAIL)

    expect(adapter.parse(source, ChannelRequest(raw_body=b"not json"))).to(equal([]))
    expect(adapter.parse(source, ChannelRequest(raw_body=b"{}"))).to(equal([]))


# ── mailgun (HMAC timestamp+token + multipart) ──────────────────────────────
def test_mailgun__verifies_signature_and_parses_inline_attachment():
    key = "signing-key"
    adapter = MailgunChannelAdapter()
    source = _source(ConnectionProvider.EMAIL, secret=key)
    # Use a fresh timestamp so the anti-replay freshness window passes.
    ts, token = str(int(time.time())), "tok"
    sig = hmac.new(key.encode(), f"{ts}{token}".encode(), hashlib.sha256).hexdigest()
    ctx = ChannelRequest(
        form={
            "timestamp": ts,
            "token": token,
            "signature": sig,
            "Message-Id": "<m-1@mg>",
            "sender": "a@b.com",
            "recipient": "in+src_abc@doxiq.dev",
            "subject": "Hi",
            "body-plain": "hello",
        },
        files={"attachment-1": ("a.pdf", "application/pdf", b"%PDF-bytes")},
    )

    expect(adapter.verify(source, ctx)).to(equal(True))
    messages = adapter.parse(source, ctx)

    expect(len(messages)).to(equal(1))
    msg = messages[0]
    expect(msg.provider_message_id).to(equal("<m-1@mg>"))
    expect(msg.attachments[0].content).to(equal(b"%PDF-bytes"))
    expect(msg.attachments[0].fetch_ref).to(be_none)


def test_mailgun__rejects_bad_signature():
    adapter = MailgunChannelAdapter()
    source = _source(ConnectionProvider.EMAIL, secret="signing-key")
    ctx = ChannelRequest(
        form={"timestamp": "1", "token": "t", "signature": "deadbeef", "Message-Id": "<x>"}
    )

    expect(adapter.verify(source, ctx)).to(equal(False))


# ── whatsapp cloud (Meta) ────────────────────────────────────────────────────
def _wa_source() -> WorkflowSource:
    return _source(
        ConnectionProvider.WHATSAPP,
        secret="access-token",
        config={"app_secret": "app-secret", "verify_token": "vt", "phone_number_id": "PN1"},
    )


def _wa_payload(message: dict) -> dict:
    return {
        "entry": [
            {"changes": [{"value": {"metadata": {"phone_number_id": "PN1"}, "messages": [message]}}]}
        ]
    }


def test_whatsapp__verifies_signature_and_parses_text():
    adapter = WhatsappCloudChannelAdapter()
    source = _wa_source()
    payload = _wa_payload({"id": "wamid.AAA", "type": "text", "from": "5215550001",
                           "text": {"body": "Pedido de helado"}})
    raw = json.dumps(payload).encode()
    header = "sha256=" + hmac.new(b"app-secret", raw, hashlib.sha256).hexdigest()
    ctx = ChannelRequest(raw_body=raw, headers={"X-Hub-Signature-256": header})

    expect(adapter.verify(source, ctx)).to(equal(True))
    messages = adapter.parse(source, ctx)

    expect(len(messages)).to(equal(1))
    msg = messages[0]
    expect(msg.provider).to(equal("whatsapp"))
    expect(msg.provider_message_id).to(equal("wamid.AAA"))
    expect(msg.recipient).to(equal("PN1"))
    expect(msg.text).to(equal("Pedido de helado"))
    expect(msg.attachments).to(equal([]))


def test_whatsapp__voice_note_defers_media_with_mime():
    adapter = WhatsappCloudChannelAdapter()
    source = _wa_source()
    payload = _wa_payload({
        "id": "wamid.BBB", "type": "audio", "from": "5215550001",
        "audio": {"id": "media-99", "mime_type": "audio/ogg", "voice": True},
    })
    messages = adapter.parse(source, ChannelRequest(raw_body=json.dumps(payload).encode()))

    expect(len(messages)).to(equal(1))
    att = messages[0].attachments[0]
    expect(att.fetch_ref).to(equal("media-99"))
    expect(att.content_type).to(equal("audio/ogg"))
    expect(att.content).to(be_none)


def test_whatsapp__rejects_invalid_signature():
    adapter = WhatsappCloudChannelAdapter()
    source = _wa_source()
    ctx = ChannelRequest(raw_body=b"{}", headers={"X-Hub-Signature-256": "sha256=bad"})

    expect(adapter.verify(source, ctx)).to(equal(False))


def test_whatsapp__hub_challenge_echoes_only_on_match():
    adapter = WhatsappCloudChannelAdapter()
    source = _wa_source()

    ok = adapter.hub_challenge(
        source, {"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "1234"}
    )
    expect(ok).to(equal("1234"))

    bad = adapter.hub_challenge(
        source, {"hub.mode": "subscribe", "hub.verify_token": "WRONG", "hub.challenge": "1234"}
    )
    expect(bad).to(be_none)


# ── registry ─────────────────────────────────────────────────────────────────
def test_registry__default_vendor_per_provider():
    expect(resolve_vendor("email", {})).to(equal("mailpit"))
    expect(resolve_vendor("whatsapp", {})).to(equal("whatsapp_cloud"))
    expect(resolve_vendor("email", {"vendor": "mailgun"})).to(equal("mailgun"))


def test_registry__resolves_known_adapters_and_none_for_unknown():
    expect(get_channel_adapter("email", "mailpit") is not None).to(equal(True))
    expect(get_channel_adapter("whatsapp", "whatsapp_cloud") is not None).to(equal(True))
    expect(get_channel_adapter("email", "nope")).to(be_none)
