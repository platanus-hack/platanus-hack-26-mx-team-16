"""hexstrike feature-flag + healthcheck (spec §10, plan §8).

hexstrike is cut to ZERO from the start of the plan. By default
``settings.ENABLE_HEXSTRIKE`` is ``False``, the ``hexstrike`` compose service does
not start (``profiles: ["hexstrike"]``) and the tool never enters
``resolve_tools``.

If it IS enabled, a healthcheck runs at worker startup: if the hexstrike MCP
server (TCP:8888) does not answer, the tool is NOT handed to ``owasp_agent`` (05)
and the advanced level falls back to the guaranteed battery (ZAP full active +
Nuclei fuzzing + sqlmap). Deploy time is NEVER spent on it.

``hexstrike_available`` returns the boolean that ``resolve_tools(hexstrike_ok=...)``
consumes: ``ENABLE_HEXSTRIKE and <TCP healthcheck OK>``.
"""

from __future__ import annotations

import asyncio

from src.common.application.logging import get_logger
from src.common.settings import settings

logger = get_logger()

#: Default hexstrike MCP host/port (the sibling container, spec §10).
HEXSTRIKE_HOST: str = getattr(settings, "HEXSTRIKE_HOST", "hexstrike")
HEXSTRIKE_PORT: int = getattr(settings, "HEXSTRIKE_PORT", 8888)
HEXSTRIKE_HEALTHCHECK_TIMEOUT_S: float = 3.0


async def check_hexstrike(
    *,
    host: str | None = None,
    port: int | None = None,
    timeout_s: float = HEXSTRIKE_HEALTHCHECK_TIMEOUT_S,
) -> bool:
    """True if the hexstrike MCP server answers on TCP (spec §10).

    A plain TCP connect attempt with a short timeout; any failure -> ``False`` (the
    worker then operates with the guaranteed fallback). Never raises.
    """
    target_host = host or HEXSTRIKE_HOST
    target_port = port or HEXSTRIKE_PORT
    try:
        fut = asyncio.open_connection(target_host, target_port)
        reader, writer = await asyncio.wait_for(fut, timeout=timeout_s)
    except (OSError, asyncio.TimeoutError, TimeoutError):
        logger.warning("hexstrike.healthcheck_failed", extra={"host": target_host, "port": target_port})
        return False
    else:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:  # noqa: BLE001 - close best-effort
            pass
        return True


async def hexstrike_available(
    *,
    host: str | None = None,
    port: int | None = None,
) -> bool:
    """Boolean fed to ``resolve_tools(hexstrike_ok=...)`` (spec §10, plan §8).

    ``True`` only when the flag is on AND the healthcheck passes. Default-off, so
    the advanced level never depends on hexstrike to produce findings.
    """
    if not settings.ENABLE_HEXSTRIKE:
        return False
    return await check_hexstrike(host=host, port=port)
