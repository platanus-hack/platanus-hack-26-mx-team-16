"""Watchdog budget + CancelToken (plan §10: test_watchdog_budget, test_cancel_token)."""

from __future__ import annotations

import asyncio

from expects import be_false, be_true, equal, expect

from src.scanning.watchdog import (
    CancelToken,
    ScanBudgetExceeded,
    run_with_watchdog,
    scan_cancel_flag_key,
)
from tests.scanning.conftest import FakeRedis


async def test_watchdog_aborts_when_budget_exceeded() -> None:
    aborted = {"value": False}

    async def slow_scan() -> str:
        try:
            await asyncio.sleep(10)  # would blow the tiny budget
        except asyncio.CancelledError:
            aborted["value"] = True
            raise
        return "done"

    # tiny budget so the test is fast; the watchdog cancels the coroutine
    expect_coro = run_with_watchdog(slow_scan(), budget_s=0)
    await_result = None
    try:
        await_result = await expect_coro
    except ScanBudgetExceeded:
        await_result = "budget"

    expect(await_result).to(equal("budget"))


async def test_watchdog_passes_through_fast_scan() -> None:
    async def fast_scan() -> str:
        return "ok"

    result = await run_with_watchdog(fast_scan(), budget_s=5)
    expect(result).to(equal("ok"))


async def test_cancel_token_reads_redis_flag() -> None:
    scan_id = "abc-123"
    redis = FakeRedis(store={scan_cancel_flag_key(scan_id): "1"})
    token = CancelToken(redis, scan_id)
    expect(await token.is_set()).to(be_true)


async def test_cancel_token_false_when_unset() -> None:
    redis = FakeRedis(store={})
    token = CancelToken(redis, "abc-123")
    expect(await token.is_set()).to(be_false)


async def test_cancel_token_false_when_no_redis() -> None:
    token = CancelToken(None, "abc-123")
    expect(await token.is_set()).to(be_false)


async def test_cancel_token_key_matches_cancel_scan_helper() -> None:
    # The key must be byte-identical to what 12's CancelScan sets.
    from src.scans.application.use_cases.cancel_scan import (
        scan_cancel_flag_key as cancel_scan_key,
    )

    expect(scan_cancel_flag_key("xyz")).to(equal(cancel_scan_key("xyz")))
    expect(CancelToken(None, "xyz").key).to(equal("scan:xyz:cancel"))


async def test_cancel_token_zero_value_is_not_set() -> None:
    redis = FakeRedis(store={"scan:s:cancel": "0"})
    token = CancelToken(redis, "s")
    expect(await token.is_set()).to(be_false)
