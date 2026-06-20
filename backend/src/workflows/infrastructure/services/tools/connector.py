"""Deterministic Tool connector (F5 · A2 · B1).

The Tool is **never** called as raw HTTP from the LLM. This connector sits
outside the model and gives every call: a host **allowlist** (per
``ConnectionAccount``, distinct from the destinations SSRF guard), a **timeout**,
**bounded retries with jitter** on transient failures, a per-account **circuit
breaker**, and — crucially — a **degraded** fallback so a 401/429/5xx or an open
breaker yields ``ToolResult(status=DEGRADED)`` instead of raising. B1: no reusable
cache; the caller persists a per-case snapshot for audit only.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import random
import time
import uuid
from urllib.parse import urlparse

import httpx

from src.common.application.helpers.webhooks.signing import (
    build_signature_headers,
    sign_payload,
)
from src.common.application.logging import get_logger
from src.common.domain.enums.tools import ToolCallStatus, ToolTransport
from src.workflows.domain.models.tool import ToolDefinition, ToolResult
from src.workflows.infrastructure.services.tools.script_runner import ScriptRunner

logger = get_logger(__name__)

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RETRIES = 2
TOOL_USER_AGENT = "Doxiq-Tools/1.0"
_BREAKER_THRESHOLD = 5  # consecutive failures before the breaker opens
_BREAKER_COOLDOWN_SECONDS = 30.0
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class ToolUrlNotAllowedError(ValueError):
    """Target host is private/reserved or not in the account's allowlist."""


def validate_tool_url(url: str, host_allowlist: list[str] | None) -> str:
    """Base SSRF guard (https, no private/loopback IP) + per-account allowlist.

    ``settings.TOOLS_ALLOW_INSECURE_HTTP`` (SOLO dev/test, default False)
    relaja https/localhost/IP-privada para apuntar tools a servicios locales;
    la allowlist por cuenta se sigue aplicando SIEMPRE.
    """
    from src.common.settings import settings

    insecure_ok = bool(getattr(settings, "TOOLS_ALLOW_INSECURE_HTTP", False))
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise ToolUrlNotAllowedError("Tool URL host is empty")
    if not insecure_ok:
        if parsed.scheme != "https":
            raise ToolUrlNotAllowedError("Tool URL must use https")
        if host == "localhost":
            raise ToolUrlNotAllowedError("Tool URL host is empty or localhost")
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            ip = None
        if ip is not None and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
            raise ToolUrlNotAllowedError("Tool URL points at a private/reserved IP")
    if host_allowlist and host not in host_allowlist:
        raise ToolUrlNotAllowedError(f"host '{host}' not in account allowlist")
    return url


class _CircuitBreaker:
    """Process-local per-key breaker. Lives in the activity worker (non-deterministic
    side), so it is safe to keep mutable state here."""

    def __init__(self) -> None:
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}

    def is_open(self, key: str, now: float) -> bool:
        return now < self._open_until.get(key, 0.0)

    def record_success(self, key: str) -> None:
        self._failures.pop(key, None)
        self._open_until.pop(key, None)

    def record_failure(self, key: str, now: float) -> None:
        count = self._failures.get(key, 0) + 1
        self._failures[key] = count
        if count >= _BREAKER_THRESHOLD:
            self._open_until[key] = now + _BREAKER_COOLDOWN_SECONDS


_breaker = _CircuitBreaker()


class DeterministicToolConnector:
    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        script_runner: ScriptRunner | None = None,
    ) -> None:
        self._client = client
        # F5 · D-D: runner del sandbox de scripts. None ⇒ fail-closed (las tools
        # PYTHON/JS degradan; jamás se ejecuta código no confiable sin sandbox).
        self._script_runner = script_runner

    async def call(
        self,
        *,
        tool: ToolDefinition,
        secret: str | None,
        host_allowlist: list[str] | None,
        args: dict,
        now: float | None = None,
        call_id: str | None = None,
    ) -> ToolResult:
        # F5: las script tools no hacen HTTP — van al runner sandbox aislado.
        if tool.transport in (ToolTransport.PYTHON, ToolTransport.JS):
            return await self._run_script(tool, args)
        now = now if now is not None else asyncio.get_event_loop().time()
        config = tool.config or {}
        url = f"{config.get('base_url', '').rstrip('/')}/{config.get('path', '').lstrip('/')}"
        method = (config.get("method") or "POST").upper()
        breaker_key = str(tool.connection_account_id)

        request_snapshot = {"url": url, "method": method, "args": args}

        try:
            validate_tool_url(url, host_allowlist)
        except ToolUrlNotAllowedError as exc:
            return self._degraded(f"ssrf_blocked: {exc}", request_snapshot)

        if _breaker.is_open(breaker_key, now):
            return self._degraded("circuit_open", request_snapshot)

        headers = dict(config.get("headers") or {})
        # `signed_body` carries the exact JSON string the HMAC signature covers;
        # when set, _send_with_retries sends those bytes verbatim (never re-dumps).
        signed_body: str | None = None
        if secret:
            auth = (config.get("auth") or "bearer").lower()
            if auth == "api_key":
                headers[config.get("api_key_header", "X-Api-Key")] = secret
            elif auth == "hmac":
                # E3: Svix-style request signing, reusing the webhook helpers.
                # signed_content = "{event_id}.{timestamp}.{body}" where body is
                # the exact compact JSON sent on the wire ("" for GET — args
                # travel as query params). event_id = ToolCallSnapshot uuid
                # (stable per call, shared by every internal retry attempt).
                event_id = call_id or str(uuid.uuid4())
                timestamp = int(time.time())
                signed_body = (
                    "" if method == "GET" else json.dumps(args, separators=(",", ":"), sort_keys=True, default=str)
                )
                try:
                    signature = sign_payload(secret, signed_body, event_id, timestamp)
                except Exception as exc:  # noqa: BLE001 — bad secret must degrade, never raise
                    return self._degraded(f"hmac_signing_failed: {type(exc).__name__}", request_snapshot)
                headers.update(build_signature_headers(event_id=event_id, timestamp=timestamp, signature=signature))
                headers["User-Agent"] = TOOL_USER_AGENT
                request_snapshot["signature"] = {"event_id": event_id, "timestamp": timestamp}
            else:
                headers["Authorization"] = f"Bearer {secret}"

        result = await self._send_with_retries(
            method, url, headers, args, config, request_snapshot, signed_body=signed_body
        )
        if result.degraded:
            _breaker.record_failure(breaker_key, now)
        else:
            _breaker.record_success(breaker_key)
        return result

    async def _send_with_retries(
        self, method, url, headers, args, config, request_snapshot, signed_body: str | None = None
    ) -> ToolResult:
        timeout = float(config.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS))
        max_retries = int(config.get("max_retries", DEFAULT_MAX_RETRIES))
        send_content = signed_body if (signed_body is not None and method != "GET") else None
        client = self._client or httpx.AsyncClient()
        owns_client = self._client is None
        last_error = "unknown"
        try:
            for attempt in range(max_retries + 1):
                try:
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        content=send_content,
                        json=args if (method != "GET" and send_content is None) else None,
                        params=args if method == "GET" else None,
                        timeout=timeout,
                    )
                    if response.status_code in _RETRYABLE_STATUS:
                        last_error = f"http_{response.status_code}"
                        await self._backoff(attempt, max_retries)
                        continue
                    if response.status_code >= 400:
                        return self._degraded(f"http_{response.status_code}", request_snapshot)
                    return ToolResult(
                        status=ToolCallStatus.OK,
                        data=_safe_json(response),
                        snapshot={
                            **request_snapshot,
                            "response_status": response.status_code,
                        },
                    )
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = type(exc).__name__
                    await self._backoff(attempt, max_retries)
            return self._degraded(last_error, request_snapshot)
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    async def _backoff(attempt: int, max_retries: int) -> None:
        if attempt >= max_retries:
            return
        # exponential base + full jitter
        delay = min(2.0**attempt, 8.0) * (0.5 + random.random() / 2)
        await asyncio.sleep(delay)

    async def _run_script(self, tool: ToolDefinition, args: dict) -> ToolResult:
        """F5 · D-D: ejecuta una script tool en el sandbox aislado. Sin runner
        provisionado degrada (fail-closed); un fallo de ejecución también degrada
        (mismo contrato B1 que HTTP — el LLM nunca ve un error crudo)."""
        config = tool.config or {}
        snapshot = {
            "transport": tool.transport.value,
            "runtime": config.get("runtime"),
            "entrypoint": config.get("entrypoint"),
            "args": args,
        }
        if self._script_runner is None:
            return self._degraded("script_sandbox_not_configured", snapshot)
        try:
            data = await self._script_runner.run(
                transport=tool.transport,
                runtime=config.get("runtime"),
                entrypoint=config.get("entrypoint"),
                code=config.get("code"),
                code_ref=config.get("code_ref"),
                args=args,
                limits=config.get("limits") or {},
            )
        except Exception as exc:  # noqa: BLE001 — un fallo de script jamás raisea; degrada
            return self._degraded(f"script_failed: {type(exc).__name__}: {exc}", snapshot)
        return ToolResult(status=ToolCallStatus.OK, data=data, snapshot=snapshot)

    @staticmethod
    def _degraded(error: str, request_snapshot: dict) -> ToolResult:
        logger.warning("tool_connector.degraded", error=error, url=request_snapshot.get("url"))
        return ToolResult(
            status=ToolCallStatus.DEGRADED,
            data=None,
            error=error,
            snapshot={**request_snapshot, "error": error},
        )


def _safe_json(response: httpx.Response) -> dict:
    try:
        body = response.json()
    except ValueError:
        return {"raw": response.text}
    return body if isinstance(body, dict) else {"data": body}
