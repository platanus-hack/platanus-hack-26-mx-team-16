"""F0 groundwork: reusable secret/token primitives."""

from expects import equal, expect

from src.common.application.helpers.secrets import (
    SECRET_PREFIX_API_KEY,
    SECRET_PREFIX_HMAC,
    SECRET_PREFIX_ROUTE_TOKEN,
    RevealableSecret,
    has_secret,
    hash_token,
    verify_token,
)
from src.common.application.helpers.webhooks.signing import generate_webhook_secret


def test_generate_webhook_secret__keeps_whsec_prefix():
    secret = generate_webhook_secret()

    expect(secret.startswith(SECRET_PREFIX_HMAC)).to(equal(True))


def test_revealable_secret__generate_applies_prefix():
    for prefix in (SECRET_PREFIX_HMAC, SECRET_PREFIX_API_KEY, SECRET_PREFIX_ROUTE_TOKEN):
        secret = RevealableSecret.generate(prefix, url_safe=True)

        expect(secret.reveal().startswith(prefix)).to(equal(True))


def test_revealable_secret__regenerate_preserves_prefix():
    original = RevealableSecret.generate(SECRET_PREFIX_API_KEY, url_safe=True)

    rotated = original.regenerate(url_safe=True)

    expect(rotated.reveal().startswith(SECRET_PREFIX_API_KEY)).to(equal(True))
    expect(rotated.reveal() == original.reveal()).to(equal(False))


def test_hash_token__is_deterministic_and_verifiable():
    token = "dxk_example-token"

    digest = hash_token(token)

    expect(digest).to(equal(hash_token(token)))
    expect(verify_token(token, digest)).to(equal(True))
    expect(verify_token("dxk_wrong", digest)).to(equal(False))


def test_has_secret__reflects_presence():
    expect(has_secret(None)).to(equal(False))
    expect(has_secret("whsec_x")).to(equal(True))
