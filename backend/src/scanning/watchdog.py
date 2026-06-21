"""Watchdog, Redis cancel token and partial-failure policy (spec §4.3, plan §4.3).

A hung scan blocks the worker and the queue, kills the live-view and ruins the
demo; with ZAP active / sqlmap / nikto, hanging is the norm. This module provides
the deterministic (LLM-free) controls:

- :class:`CancelToken` — reads the Redis cancel flag (``scan:{id}:cancel``) the API
  sets via ``CancelScan`` (12). Checked BEFORE each tool and at the start of
  ``run_tool``; best-effort, never aborts a tool mid-run, only prevents launching
  the next one.
- :func:`run_with_watchdog` — wraps the scan coroutine in
  ``asyncio.wait_for(..., timeout=SCAN_BUDGET_S)``; when the global ~8min budget is
  exhausted it cancels the scan coroutine, aborting the remaining in-flight tools
  instead of letting a late tool consume everything.

Partial failure is enforced inside ``run_tool`` (each tool in its own
``try/except`` -> a non-null ``ToolResult.coverage_note`` instead of a raised
exception). 05 turns that note into a Finding-meta and continues.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Protocol, TypeVar

from src.common.application.logging import get_logger
from src.common.settings import settings

logger = get_logger()

T = TypeVar("T")

#: Global per-scan budget (seconds). Defaults to the 02-owned setting (~8 min).
#: A late tool that would blow this is aborted by the watchdog (spec §4.2/§4.3).
SCAN_BUDGET_S: int = settings.SCAN_GLOBAL_BUDGET_SECONDS


class ScanBudgetExceeded(Exception):
    """Raised by :func:`run_with_watchdog` when the global budget is exhausted.

    The scan closes as ``partial`` (it produced whatever findings it had before
    the budget ran out); it never hangs. NOT a ``DomainError`` — this is an
    internal worker-flow signal, not a user-facing API error.
    """


def scan_cancel_flag_key(scan_id: object) -> str:
    """Redis key the worker polls between tools (shared with 12's ``CancelScan``).

    Re-exported here so the engine has one import surface; byte-identical to
    ``src.scans.application.use_cases.cancel_scan.scan_cancel_flag_key``.
    """
    return f"scan:{scan_id}:cancel"


class _RedisLike(Protocol):
    async def get(self, key: str) -> object: ...


class CancelToken:
    """Reads the Redis cancel flag for a scan (plan §4.3).

    ``redis`` is the ``decode_responses=True`` client injected into the SAQ worker
    ctx (``config/tasks.py`` ``startup``); ``scan_id`` is the scan uuid. ``is_set``
    is best-effort: a Redis hiccup must never abort a scan, so it returns ``False``
    on error (fail-open — the watchdog still bounds the total time).
    """

    __slots__ = ("_key", "_redis", "_scan_id")

    def __init__(self, redis: _RedisLike | None, scan_id: object) -> None:
        self._redis = redis
        self._scan_id = scan_id
        self._key = scan_cancel_flag_key(scan_id)

    @property
    def scan_id(self) -> object:
        return self._scan_id

    @property
    def key(self) -> str:
        return self._key

    async def is_set(self) -> bool:
        """True if ``scan:{id}:cancel`` is set in Redis (checked between tools)."""
        if self._redis is None:
            return False
        try:
            value = await self._redis.get(self._key)
        except Exception:  # pragma: no cover - defensive; Redis must never abort
            logger.warning("cancel_token.redis_error", extra={"scan_id": str(self._scan_id)})
            return False
        return value not in (None, "", "0", b"0", 0, False)


async def run_with_watchdog(
    scan_coro: Awaitable[T],
    *,
    budget_s: int | None = None,
) -> T:
    """Run ``scan_coro`` under the global budget watchdog (spec §4.3).

    On timeout it cancels the coroutine (aborting in-flight tools) and raises
    :class:`ScanBudgetExceeded`. The caller (05's worker flow) catches it, closes
    the scan as ``partial`` and persists the accumulated findings — the scan never
    hangs the worker.
    """
    timeout = SCAN_BUDGET_S if budget_s is None else budget_s
    try:
        return await asyncio.wait_for(scan_coro, timeout=timeout)
    except (asyncio.TimeoutError, TimeoutError) as exc:
        logger.warning("watchdog.budget_exceeded", extra={"budget_s": timeout})
        raise ScanBudgetExceeded(
            f"scan exceeded its global budget of {timeout}s; remaining tools aborted"
        ) from exc
