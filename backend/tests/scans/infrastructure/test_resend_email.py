"""Infra tests for the Resend email service (08-ranking-watchlists §5.4).
HTTP mocked via monkeypatching httpx.AsyncClient; no network."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from expects import be_none, contain, equal, expect

from src.scans.infrastructure.services import resend_email
from src.scans.infrastructure.services.resend_email import ResendEmailService


class _FakeClient:
    def __init__(self, *args, **kwargs):
        self.posted = None
        self.response = MagicMock()
        self.response.raise_for_status = MagicMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, json=None, headers=None):
        self.posted = {"url": url, "json": json, "headers": headers}
        type(self).last = self.posted
        return self.response


async def test_resend_posts_with_api_key_and_sender(monkeypatch):
    monkeypatch.setattr(resend_email.httpx, "AsyncClient", _FakeClient)

    service = ResendEmailService(api_key="re_test_key")
    await service.send_email(
        subject="Owliver alert: x.gob.mx",
        sender="alerts@owliver.mx",
        recipients=["owner@example.com"],
        template_name="monitoring_alert",
        context={"body": "grade dropped B -> F"},
    )

    posted = _FakeClient.last
    expect(posted["url"]).to(contain("resend.com"))
    expect(posted["headers"]["Authorization"]).to(equal("Bearer re_test_key"))
    expect(posted["json"]["from"]).to(equal("alerts@owliver.mx"))
    expect(posted["json"]["to"]).to(equal(["owner@example.com"]))
    expect(posted["json"]["text"]).to(contain("grade dropped"))


async def test_resend_without_api_key_degrades(monkeypatch):
    called = {"posted": False}

    class _Boom:
        def __init__(self, *a, **k):
            called["posted"] = True

    monkeypatch.setattr(resend_email.httpx, "AsyncClient", _Boom)

    service = ResendEmailService(api_key=None)
    # Must not raise and must not attempt any HTTP.
    await service.send_email(
        subject="s", sender="from@x.com", recipients=["to@x.com"],
        template_name="monitoring_alert", context={},
    )
    expect(called["posted"]).to(equal(False))


async def test_resend_http_error_is_swallowed(monkeypatch):
    class _ErrClient(_FakeClient):
        async def post(self, url, json=None, headers=None):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(resend_email.httpx, "AsyncClient", _ErrClient)

    service = ResendEmailService(api_key="re_test_key")
    # Degrades gracefully — never poisons the monitoring run.
    await service.send_email(
        subject="s", sender="from@x.com", recipients=["to@x.com"],
        template_name="monitoring_alert", context={"body": "b"},
    )
