"""E6 · W5: per-provider channel signature verifiers (Meta + Mailgun)."""

from __future__ import annotations

import hashlib
import hmac

from expects import equal, expect

from src.connections.domain.services.channel_auth import (
    verify_mailgun_signature,
    verify_meta_signature,
)


def _meta_header(app_secret: str, raw_body: bytes) -> str:
    return "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()


def _mailgun_sig(signing_key: str, timestamp: str, token: str) -> str:
    return hmac.new(
        signing_key.encode(), f"{timestamp}{token}".encode(), hashlib.sha256
    ).hexdigest()


def test_meta__accepts_valid_signature_over_raw_body():
    secret, body = "app-secret", b'{"entry":[]}'
    header = _meta_header(secret, body)

    expect(verify_meta_signature(secret, body, header)).to(equal(True))


def test_meta__rejects_tampered_body_wrong_secret_and_missing_header():
    secret, body = "app-secret", b'{"entry":[]}'
    header = _meta_header(secret, body)

    expect(verify_meta_signature(secret, b'{"entry":[1]}', header)).to(equal(False))
    expect(verify_meta_signature("other", body, header)).to(equal(False))
    expect(verify_meta_signature(secret, body, None)).to(equal(False))
    # Header without the sha256= prefix is rejected.
    expect(verify_meta_signature(secret, body, "deadbeef")).to(equal(False))


def test_mailgun__accepts_valid_signature():
    key, ts, token = "signing-key", "1700000000", "abc123"
    sig = _mailgun_sig(key, ts, token)

    # Pin ``now`` to the signed timestamp so the freshness window passes.
    expect(verify_mailgun_signature(key, ts, token, sig, now=1700000000)).to(equal(True))


def test_mailgun__rejects_tampered_and_missing_fields():
    key, ts, token = "signing-key", "1700000000", "abc123"
    sig = _mailgun_sig(key, ts, token)

    expect(verify_mailgun_signature(key, ts, "other-token", sig, now=1700000000)).to(equal(False))
    expect(verify_mailgun_signature("wrong-key", ts, token, sig, now=1700000000)).to(equal(False))
    expect(verify_mailgun_signature(key, None, token, sig, now=1700000000)).to(equal(False))
    expect(verify_mailgun_signature(key, ts, token, None, now=1700000000)).to(equal(False))
