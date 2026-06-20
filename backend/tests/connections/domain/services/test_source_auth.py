"""F8 · D3: ingest Source authentication (api_key + HMAC + replay)."""

from uuid import uuid4

from expects import equal, expect

from src.common.application.helpers.secrets import (
    SECRET_PREFIX_HMAC,
    generate_base64_secret,
    hash_token,
)
from src.common.domain.enums.sources import SourceAuthMode
from src.connections.domain.models.workflow_source import WorkflowSource
from src.connections.domain.services.source_auth import (
    compute_source_signature,
    verify_source_auth,
)

_API_KEY = "dxk_secret-key"


def _source(auth_mode: SourceAuthMode, secret: str) -> WorkflowSource:
    return WorkflowSource(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        route_token="src_abc",
        auth_mode=auth_mode,
        secret=secret,
    )


def test_api_key__accepts_matching_key_rejects_others():
    source = _source(SourceAuthMode.API_KEY, hash_token(_API_KEY))

    expect(verify_source_auth(source, api_key=_API_KEY)).to(equal(True))
    expect(verify_source_auth(source, api_key="dxk_wrong")).to(equal(False))
    expect(verify_source_auth(source, api_key=None)).to(equal(False))


def test_hmac__accepts_valid_signature():
    secret = generate_base64_secret(SECRET_PREFIX_HMAC)
    source = _source(SourceAuthMode.HMAC, secret)
    ts, body = 1000, '{"x":1}'
    sig = compute_source_signature(secret, ts, body)

    ok = verify_source_auth(source, signature=sig, timestamp=ts, body=body, now=1000)

    expect(ok).to(equal(True))


def test_hmac__rejects_tampered_body_and_stale_timestamp():
    secret = generate_base64_secret(SECRET_PREFIX_HMAC)
    source = _source(SourceAuthMode.HMAC, secret)
    ts, body = 1000, '{"x":1}'
    sig = compute_source_signature(secret, ts, body)

    expect(verify_source_auth(source, signature=sig, timestamp=ts, body='{"x":2}', now=1000)).to(equal(False))
    # stale timestamp (replay) beyond the skew window
    expect(verify_source_auth(source, signature=sig, timestamp=ts, body=body, now=1000 + 9999)).to(equal(False))


def test_disabled_source__never_authenticates():
    source = _source(SourceAuthMode.API_KEY, hash_token(_API_KEY))
    source.enabled = False

    expect(verify_source_auth(source, api_key=_API_KEY)).to(equal(False))
