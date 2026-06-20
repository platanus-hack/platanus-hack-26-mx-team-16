"""F5: deterministic Tool connector — SSRF allowlist, circuit breaker, degraded.

E3: HMAC request signing (Svix-style Doxiq-Id/Doxiq-Timestamp/Doxiq-Signature)."""

import base64
import hashlib
import hmac as hmac_lib
from uuid import UUID

import httpx
from expects import contain, equal, expect

from src.common.application.helpers.webhooks.signing import sign_payload
from src.common.domain.enums.tools import ToolCallStatus
from src.workflows.domain.models.tool import ToolDefinition
from src.workflows.infrastructure.services.tools.connector import (
    DeterministicToolConnector,
    TOOL_USER_AGENT,
    ToolUrlNotAllowedError,
    _BREAKER_THRESHOLD,
    _CircuitBreaker,
    validate_tool_url,
)

_ACCOUNT = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _tool(**config) -> ToolDefinition:
    return ToolDefinition(
        uuid=UUID("11111111-1111-1111-1111-111111111111"),
        tenant_id=UUID("22222222-2222-2222-2222-222222222222"),
        workflow_id=UUID("33333333-3333-3333-3333-333333333333"),
        name="lookup_judge",
        display_name="Lookup Judge",
        connection_account_id=_ACCOUNT,
        config={"base_url": "https://api.example.com", "path": "/lookup", "max_retries": 0, **config},
    )


def _connector(handler) -> DeterministicToolConnector:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return DeterministicToolConnector(client=client)


# ── SSRF / allowlist ────────────────────────────────────────────────────────


def test_validate_tool_url__rejects_non_https_private_and_unlisted(monkeypatch):
    # Arrange — el guard SEGURO es el default de prod; el .env de dev puede
    # traer TOOLS_ALLOW_INSECURE_HTTP=true, así que se pinea explícito.
    from src.common.settings import settings

    monkeypatch.setattr(settings, "TOOLS_ALLOW_INSECURE_HTTP", False, raising=False)

    for bad in ("http://api.example.com/x", "https://127.0.0.1/x", "https://localhost/x"):
        try:
            validate_tool_url(bad, ["api.example.com"])
            raise AssertionError(f"expected rejection for {bad}")
        except ToolUrlNotAllowedError:
            pass
    try:
        validate_tool_url("https://evil.com/x", ["api.example.com"])
        raise AssertionError("expected allowlist rejection")
    except ToolUrlNotAllowedError:
        pass


def test_validate_tool_url__allows_listed_https():
    expect(validate_tool_url("https://api.example.com/x", ["api.example.com"])).to(equal("https://api.example.com/x"))


def test_validate_tool_url__insecure_escape_keeps_allowlist(monkeypatch):
    # Arrange — el escape dev (http/localhost) JAMÁS desactiva la allowlist.
    from src.common.settings import settings

    monkeypatch.setattr(settings, "TOOLS_ALLOW_INSECURE_HTTP", True, raising=False)

    # Act + Assert — http/localhost pasan con el flag…
    expect(validate_tool_url("http://localhost:9998/x", ["localhost"])).to(equal("http://localhost:9998/x"))
    # …pero un host fuera de la allowlist sigue bloqueado.
    try:
        validate_tool_url("http://evil.com/x", ["localhost"])
        raise AssertionError("expected allowlist rejection")
    except ToolUrlNotAllowedError:
        pass


# ── connector behaviour ─────────────────────────────────────────────────────


async def test_call__ok_returns_data():
    connector = _connector(lambda req: httpx.Response(200, json={"judge": "Smith"}))

    result = await connector.call(
        tool=_tool(), secret="s", host_allowlist=["api.example.com"], args={"q": "x"}, now=0.0
    )

    expect(result.status).to(equal(ToolCallStatus.OK))
    expect(result.data).to(equal({"judge": "Smith"}))


async def test_call__http_401_degrades_without_raising():
    connector = _connector(lambda req: httpx.Response(401, json={"error": "nope"}))

    result = await connector.call(tool=_tool(), secret="bad", host_allowlist=["api.example.com"], args={}, now=0.0)

    expect(result.status).to(equal(ToolCallStatus.DEGRADED))
    expect(result.data).to(equal(None))
    expect(result.error).to(equal("http_401"))


async def test_call__ssrf_block_degrades_and_never_calls():
    called = {"n": 0}

    def handler(req):
        called["n"] += 1
        return httpx.Response(200, json={})

    connector = _connector(handler)
    result = await connector.call(tool=_tool(), secret="s", host_allowlist=["other.com"], args={}, now=0.0)

    expect(result.status).to(equal(ToolCallStatus.DEGRADED))
    expect(called["n"]).to(equal(0))


# ── HMAC signing (E3) ───────────────────────────────────────────────────────

_HMAC_KEY = b"k" * 32
_HMAC_SECRET = "whsec_" + base64.b64encode(_HMAC_KEY).decode()


async def test_call__hmac_signs_post_body_with_verifiable_svix_headers():
    seen: dict = {}

    def handler(req):
        seen["headers"] = req.headers
        seen["body"] = req.content.decode()
        return httpx.Response(200, json={"ok": True})

    connector = _connector(handler)

    result = await connector.call(
        tool=_tool(auth="hmac"),
        secret=_HMAC_SECRET,
        host_allowlist=["api.example.com"],
        args={"b": 2, "a": 1},
        now=0.0,
        call_id="call-123",
    )

    expect(result.status).to(equal(ToolCallStatus.OK))
    # Body is the exact compact, key-sorted JSON the signature covers.
    expect(seen["body"]).to(equal('{"a":1,"b":2}'))
    expect(seen["headers"]["Doxiq-Id"]).to(equal("call-123"))
    expect(seen["headers"]["User-Agent"]).to(equal(TOOL_USER_AGENT))
    timestamp = int(seen["headers"]["Doxiq-Timestamp"])
    # Verify with the shared helper AND an independent HMAC recomputation.
    expect(seen["headers"]["Doxiq-Signature"]).to(
        equal(sign_payload(_HMAC_SECRET, seen["body"], "call-123", timestamp))
    )
    signed_content = f"call-123.{timestamp}.{seen['body']}".encode()
    manual = "v1," + base64.b64encode(hmac_lib.new(_HMAC_KEY, signed_content, hashlib.sha256).digest()).decode()
    expect(seen["headers"]["Doxiq-Signature"]).to(equal(manual))
    expect(result.snapshot["signature"]["event_id"]).to(equal("call-123"))


async def test_call__hmac_get_signs_empty_body_and_keeps_query_args():
    seen: dict = {}

    def handler(req):
        seen["headers"] = req.headers
        seen["url"] = str(req.url)
        seen["body"] = req.content.decode()
        return httpx.Response(200, json={"ok": True})

    connector = _connector(handler)

    result = await connector.call(
        tool=_tool(auth="hmac", method="GET"),
        secret=_HMAC_SECRET,
        host_allowlist=["api.example.com"],
        args={"q": "x"},
        now=0.0,
        call_id="call-9",
    )

    expect(result.status).to(equal(ToolCallStatus.OK))
    expect(seen["body"]).to(equal(""))
    expect(seen["url"]).to(contain("q=x"))
    timestamp = int(seen["headers"]["Doxiq-Timestamp"])
    expect(seen["headers"]["Doxiq-Signature"]).to(equal(sign_payload(_HMAC_SECRET, "", "call-9", timestamp)))


async def test_call__bearer_and_api_key_modes_unchanged():
    seen: dict = {}

    def handler(req):
        seen.setdefault("auths", []).append((req.headers.get("Authorization"), req.headers.get("X-Custom-Key")))
        return httpx.Response(200, json={})

    connector = _connector(handler)
    await connector.call(tool=_tool(), secret="tok", host_allowlist=["api.example.com"], args={}, now=0.0)
    await connector.call(
        tool=_tool(auth="api_key", api_key_header="X-Custom-Key"),
        secret="tok",
        host_allowlist=["api.example.com"],
        args={},
        now=0.0,
    )

    expect(seen["auths"][0]).to(equal(("Bearer tok", None)))
    expect(seen["auths"][1]).to(equal((None, "tok")))


# ── circuit breaker ─────────────────────────────────────────────────────────


def test_circuit_breaker__opens_after_threshold_and_closes_on_success():
    breaker = _CircuitBreaker()

    for _ in range(_BREAKER_THRESHOLD):
        breaker.record_failure("k", now=0.0)

    expect(breaker.is_open("k", now=1.0)).to(equal(True))

    breaker.record_success("k")
    expect(breaker.is_open("k", now=1.0)).to(equal(False))
