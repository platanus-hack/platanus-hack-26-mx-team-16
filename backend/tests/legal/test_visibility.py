"""Default-visibility invariant (01-legal §2.3) — pure domain, property-style.

Invariant: ONLY a gov + passive (basic) + un-owned scan is public; any active
level, or any scan with an owner, defaults to private. A user-initiated active
scan therefore never reaches the public ranking automatically.
"""

from __future__ import annotations

import pytest
from expects import equal, expect

from src.common.domain.enums.scans import ScanLevel, ScanVisibility
from src.common.domain.legal.levels import default_visibility, is_active

_ALL_LEVELS = list(ScanLevel)
_BOOLS = [True, False]


def test_gov_basic_unowned_is_public() -> None:
    visibility = default_visibility(
        is_gov=True, level=ScanLevel.BASICO, has_owner=False
    )
    expect(visibility).to(equal(ScanVisibility.PUBLIC))


@pytest.mark.parametrize("level", [ScanLevel.INTERMEDIO, ScanLevel.AVANZADO])
def test_gov_active_unowned_is_private(level: ScanLevel) -> None:
    visibility = default_visibility(is_gov=True, level=level, has_owner=False)
    expect(visibility).to(equal(ScanVisibility.PRIVATE))


@pytest.mark.parametrize("level", _ALL_LEVELS)
def test_owned_scan_is_always_private(level: ScanLevel) -> None:
    # Having an owner forces private regardless of gov/level.
    for is_gov in _BOOLS:
        visibility = default_visibility(
            is_gov=is_gov, level=level, has_owner=True
        )
        expect(visibility).to(equal(ScanVisibility.PRIVATE))


@pytest.mark.parametrize("level", _ALL_LEVELS)
def test_non_gov_is_always_private(level: ScanLevel) -> None:
    for has_owner in _BOOLS:
        visibility = default_visibility(
            is_gov=False, level=level, has_owner=has_owner
        )
        expect(visibility).to(equal(ScanVisibility.PRIVATE))


@pytest.mark.parametrize("is_gov", _BOOLS)
@pytest.mark.parametrize("level", _ALL_LEVELS)
@pytest.mark.parametrize("has_owner", _BOOLS)
def test_public_iff_gov_passive_unowned(
    is_gov: bool, level: ScanLevel, has_owner: bool
) -> None:
    # Property: public <=> gov AND passive AND no owner. Active never public.
    visibility = default_visibility(
        is_gov=is_gov, level=level, has_owner=has_owner
    )
    should_be_public = is_gov and not has_owner and not is_active(level)
    expected = ScanVisibility.PUBLIC if should_be_public else ScanVisibility.PRIVATE
    expect(visibility).to(equal(expected))
    if is_active(level):
        expect(visibility).to(equal(ScanVisibility.PRIVATE))
