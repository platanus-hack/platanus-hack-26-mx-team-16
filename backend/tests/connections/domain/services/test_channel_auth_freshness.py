"""Regression (E6 · W5 · BUG 4): Mailgun signatures need timestamp freshness.

``verify_mailgun_signature`` HMACs only ``timestamp+token`` and previously never
checked the timestamp, so a leaked ``(timestamp, token, signature)`` triple was
replayable forever (a fresh ``Message-Id`` per replay defeats dedup). These tests
pin ``now`` to keep them deterministic and assert the anti-replay window.
"""

from __future__ import annotations

import hashlib
import hmac

from expects import equal, expect

from src.connections.domain.services.channel_auth import (
    DEFAULT_MAX_SKEW_SECONDS,
    verify_mailgun_signature,
)


def _sig(signing_key: str, timestamp: str, token: str) -> str:
    return hmac.new(
        signing_key.encode(), f"{timestamp}{token}".encode(), hashlib.sha256
    ).hexdigest()


def test_mailgun_freshness__accepts_a_fresh_timestamp():
    key, ts, token = "signing-key", "1700000000", "abc123"
    sig = _sig(key, ts, token)

    # ``now`` within the window of the signed timestamp -> accepted.
    expect(verify_mailgun_signature(key, ts, token, sig, now=1700000000)).to(equal(True))
    expect(
        verify_mailgun_signature(key, ts, token, sig, now=1700000000 + DEFAULT_MAX_SKEW_SECONDS)
    ).to(equal(True))


def test_mailgun_freshness__rejects_a_stale_timestamp_replay():
    key, ts, token = "signing-key", "1700000000", "abc123"
    sig = _sig(key, ts, token)

    # A valid, correctly-signed triple replayed well outside the window is rejected.
    stale_now = 1700000000 + DEFAULT_MAX_SKEW_SECONDS + 1
    expect(verify_mailgun_signature(key, ts, token, sig, now=stale_now)).to(equal(False))
    # Future-dated beyond the window is rejected too (abs skew).
    future_now = 1700000000 - DEFAULT_MAX_SKEW_SECONDS - 1
    expect(verify_mailgun_signature(key, ts, token, sig, now=future_now)).to(equal(False))


def test_mailgun_freshness__non_integer_timestamp_is_rejected_not_500():
    key, token = "signing-key", "abc123"
    sig = _sig(key, "not-an-int", token)

    expect(verify_mailgun_signature(key, "not-an-int", token, sig, now=1700000000)).to(
        equal(False)
    )
