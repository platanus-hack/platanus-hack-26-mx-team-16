"""Automatic-only-passive invariant (01-legal §2.2) — pure domain.

Invariant: the only level the scheduler / seed-cron may auto-emit is ``basico``;
forcing any active level through the guard raises ``AutomaticActiveScanError``.

This mirrors the guard 08 must place before enqueuing an automatic job:

    if level not in AUTOMATIC_ALLOWED_LEVELS:
        raise AutomaticActiveScanError(...)
"""

from __future__ import annotations

import pytest
from expects import contain, equal, expect, raise_error

from src.common.domain.enums.scans import ScanLevel
from src.common.domain.legal.exceptions import AutomaticActiveScanError
from src.common.domain.legal.levels import AUTOMATIC_ALLOWED_LEVELS, is_active


def _scheduler_guard(level: ScanLevel) -> ScanLevel:
    """Reference guard every automatic trigger path (08) must apply."""
    if level not in AUTOMATIC_ALLOWED_LEVELS:
        raise AutomaticActiveScanError(context={"level": str(level)})
    return level


def test_only_basico_is_auto_emittable() -> None:
    expect(AUTOMATIC_ALLOWED_LEVELS).to(equal(frozenset({ScanLevel.BASICO})))


def test_no_active_level_is_auto_allowed() -> None:
    for level in (ScanLevel.INTERMEDIO, ScanLevel.AVANZADO):
        expect(AUTOMATIC_ALLOWED_LEVELS).not_to(contain(level))
        expect(is_active(level)).to(equal(True))


def test_basico_passes_the_guard() -> None:
    expect(_scheduler_guard(ScanLevel.BASICO)).to(equal(ScanLevel.BASICO))


@pytest.mark.parametrize("level", [ScanLevel.INTERMEDIO, ScanLevel.AVANZADO])
def test_active_level_through_guard_raises(level: ScanLevel) -> None:
    expect(lambda: _scheduler_guard(level)).to(
        raise_error(AutomaticActiveScanError)
    )


def test_automatic_active_error_is_500() -> None:
    error = AutomaticActiveScanError()
    expect(error.status_code).to(equal(500))
    expect(error.code).to(equal("automatic_active_forbidden"))
