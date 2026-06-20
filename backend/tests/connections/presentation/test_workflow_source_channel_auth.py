"""Regression (E6 · W5 · BUG 1): mailpit must not bypass auth in production.

The public ``/v1/channels/email/{route_token}`` endpoint trusts the vendor
adapter's ``verify``. The default email vendor is ``mailpit``, whose ``verify``
returns ``True`` unconditionally, and the route_token is published in the inbound
alias (not a secret) — so a production EMAIL source created with the default
config would accept UNSIGNED forged webhooks.

Defense is layered:
- ``create_source`` (``_validate_channel_config``) rejects channel sources that
  resolve to a no-signature vendor in production (422).
- ``resolve_vendor`` does not silently fall back to mailpit in production.
- ``MailpitChannelAdapter.verify`` hard-fails in production regardless.

Dev/test behavior is unchanged: mailpit stays the working email default.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.enums.common import Environment
from src.common.domain.enums.connections import ConnectionProvider
from src.common.domain.exceptions._base import DomainError
from src.connections.domain.channels.base import ChannelRequest
from src.connections.domain.models.workflow_source import WorkflowSource
from src.connections.infrastructure.channels import email_mailpit, registry
from src.connections.presentation.endpoints import workflow_source as ws


def _email_source(config: dict | None = None) -> WorkflowSource:
    return WorkflowSource(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        provider=ConnectionProvider.EMAIL,
        route_token="src_published_in_alias",
        secret=None,
        config=config or {},
    )


@pytest.fixture
def prod(monkeypatch):
    """Flip every settings reader in this cluster to production at once.

    All three modules share the ``src.common.settings.settings`` singleton, so a
    single attribute swap is seen by registry, mailpit and create_source.
    """
    monkeypatch.setattr(registry.settings, "ENVIRONMENT", Environment.production)


@pytest.fixture
def dev(monkeypatch):
    monkeypatch.setattr(registry.settings, "ENVIRONMENT", Environment.development)


# ── create_source validation (BUG 1, layer 1) ───────────────────────────────
def test_create_source__rejects_default_email_vendor_in_production(prod):
    # No explicit vendor -> would resolve to mailpit -> 422 in prod.
    with pytest.raises(DomainError) as exc:
        ws._validate_channel_config(ConnectionProvider.EMAIL, {})

    expect(exc.value.code).to(equal("source.unsigned_channel_vendor"))
    expect(exc.value.status_code).to(equal(422))


def test_create_source__rejects_explicit_mailpit_vendor_in_production(prod):
    with pytest.raises(DomainError):
        ws._validate_channel_config(ConnectionProvider.EMAIL, {"vendor": "mailpit"})


def test_create_source__allows_signed_email_vendor_in_production(prod):
    # mailgun is a signed vendor -> accepted (no raise).
    ws._validate_channel_config(ConnectionProvider.EMAIL, {"vendor": "mailgun"})


def test_create_source__whatsapp_default_is_signed_so_allowed_in_production(prod):
    # The default whatsapp vendor (whatsapp_cloud) is signed.
    ws._validate_channel_config(ConnectionProvider.WHATSAPP, {})


def test_create_source__non_channel_provider_is_not_validated(prod):
    # WEBHOOK is the API-ingest provider, not a native channel — untouched.
    ws._validate_channel_config(ConnectionProvider.WEBHOOK, {})


def test_create_source__default_email_vendor_is_allowed_in_dev(dev):
    # Dev keeps mailpit as the working default — no raise.
    ws._validate_channel_config(ConnectionProvider.EMAIL, {})


# ── resolve_vendor defensive guard (BUG 1, layer 2) ──────────────────────────
def test_resolve_vendor__does_not_fall_back_to_mailpit_in_production(prod):
    # Empty -> no adapter resolves -> endpoint 404s rather than accepting forgeries.
    expect(registry.resolve_vendor("email", {})).to(equal(""))
    expect(registry.get_channel_adapter("email", registry.resolve_vendor("email", {}))).to(be_none)
    # WhatsApp default is signed and unaffected.
    expect(registry.resolve_vendor("whatsapp", {})).to(equal("whatsapp_cloud"))


def test_resolve_vendor__keeps_mailpit_default_in_dev(dev):
    expect(registry.resolve_vendor("email", {})).to(equal("mailpit"))


# ── MailpitChannelAdapter.verify hard-fail (BUG 1, layer 3) ──────────────────
def test_mailpit_verify__rejects_in_production_even_for_explicit_source(prod):
    adapter = email_mailpit.MailpitChannelAdapter()

    expect(adapter.verify(_email_source(), ChannelRequest(raw_body=b"{}"))).to(equal(False))


def test_mailpit_verify__accepts_in_dev(dev):
    adapter = email_mailpit.MailpitChannelAdapter()

    expect(adapter.verify(_email_source(), ChannelRequest(raw_body=b"{}"))).to(equal(True))
