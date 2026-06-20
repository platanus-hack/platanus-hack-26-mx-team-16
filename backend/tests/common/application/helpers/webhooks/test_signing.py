import base64
import hashlib
import hmac

from expects import be_true, contain, equal, expect

from src.common.application.helpers.webhooks.signing import (
    SECRET_PREFIX,
    build_signature_headers,
    generate_webhook_secret,
    sign_payload,
)


def test_sign_payload__is_deterministic_and_versioned():
    secret = generate_webhook_secret()

    first = sign_payload(secret, '{"a":1}', "evt_1", 1700000000)
    second = sign_payload(secret, '{"a":1}', "evt_1", 1700000000)

    expect(first).to(equal(second))
    expect(first.startswith("v1,")).to(be_true)


def test_sign_payload__changes_with_body():
    secret = generate_webhook_secret()

    a = sign_payload(secret, '{"a":1}', "evt_1", 1700000000)
    b = sign_payload(secret, '{"a":2}', "evt_1", 1700000000)

    expect(a).not_to(equal(b))


def test_sign_payload__matches_manual_hmac_over_signed_content():
    secret = generate_webhook_secret()
    body, event_id, timestamp = '{"x":true}', "evt_42", 1700000000
    key = base64.b64decode(secret.removeprefix(SECRET_PREFIX))
    digest = hmac.new(key, f"{event_id}.{timestamp}.{body}".encode(), hashlib.sha256).digest()
    expected = "v1," + base64.b64encode(digest).decode()

    result = sign_payload(secret, body, event_id, timestamp)

    expect(result).to(equal(expected))


def test_generate_webhook_secret__is_prefixed_and_decodes_to_32_bytes():
    secret = generate_webhook_secret()

    expect(secret.startswith(SECRET_PREFIX)).to(be_true)
    expect(len(base64.b64decode(secret.removeprefix(SECRET_PREFIX)))).to(equal(32))


def test_build_signature_headers__sets_doxiq_headers():
    headers = build_signature_headers(event_id="evt_1", timestamp=1700000000, signature="v1,abc")

    expect(headers["Doxiq-Id"]).to(equal("evt_1"))
    expect(headers["Doxiq-Timestamp"]).to(equal("1700000000"))
    expect(headers["Doxiq-Signature"]).to(equal("v1,abc"))
    expect(headers["Content-Type"]).to(equal("application/json"))
    expect(headers["User-Agent"]).to(contain("Doxiq-Webhooks"))
