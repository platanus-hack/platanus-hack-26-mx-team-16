"""resolve_tools mapping + gov/basic passive-profile enforcement (plan §10).

Tests the RESOLVER (04), not the legal contract itself (01 owns that). We assert
the materialized result respects the passive floor and the cumulative ladder.
"""

from __future__ import annotations

from expects import be_empty, contain, equal, expect, raise_error

from src.common.domain.enums.scans import ScanLevel
from src.common.domain.legal.passive_profile import PassiveProfileViolation
from src.scanning.resolver import resolve_tools
from src.scans.domain.enums.tool_id import ToolId


def _tool_ids(invocations) -> set[str]:
    return {str(inv.tool) for inv in invocations}


def test_gov_basic_is_within_passive_profile() -> None:
    tools = resolve_tools(is_gov=True, level=ScanLevel.BASICO)
    ids = _tool_ids(tools)
    # Exactly the legal passive floor: testssl / security_headers / whatweb / nuclei.
    expect(ids).to(equal({"testssl", "security_headers", "whatweb", "nuclei"}))


def test_gov_basic_excludes_crawlers() -> None:
    ids = _tool_ids(resolve_tools(is_gov=True, level=ScanLevel.BASICO))
    # ZAP spider/baseline and katana are ABSENT by construction for gov/basic.
    expect(ids).not_to(contain("katana"))
    expect(ids).not_to(contain("zap_baseline"))
    expect(ids).not_to(contain("zap_full_active"))


def test_levels_are_cumulative_non_gov() -> None:
    basic = _tool_ids(resolve_tools(is_gov=False, level=ScanLevel.BASICO))
    inter = _tool_ids(resolve_tools(is_gov=False, level=ScanLevel.INTERMEDIO))
    adv = _tool_ids(resolve_tools(is_gov=False, level=ScanLevel.AVANZADO))
    # basic ⊂ intermediate ⊂ advanced
    expect(basic - inter).to(be_empty)
    expect(inter - adv).to(be_empty)
    # advanced adds bounded exploitation tools
    expect(adv).to(contain("zap_full_active"))
    expect(adv).to(contain("sqlmap"))


def test_hexstrike_absent_without_flag() -> None:
    adv = _tool_ids(resolve_tools(is_gov=False, level=ScanLevel.AVANZADO, hexstrike_ok=False))
    expect(adv).not_to(contain("hexstrike"))


def test_hexstrike_appended_only_when_ok_and_advanced() -> None:
    adv = _tool_ids(resolve_tools(is_gov=False, level=ScanLevel.AVANZADO, hexstrike_ok=True))
    expect(adv).to(contain("hexstrike"))
    # never appended below advanced
    inter = _tool_ids(resolve_tools(is_gov=False, level=ScanLevel.INTERMEDIO, hexstrike_ok=True))
    expect(inter).not_to(contain("hexstrike"))


def test_demo_short_circuits_level() -> None:
    demo = _tool_ids(resolve_tools(is_gov=True, level=ScanLevel.AVANZADO, demo=True))
    # demo profile is a curated fast subset, NOT the advanced battery
    expect(demo).not_to(contain("zap_full_active"))
    expect(demo).not_to(contain("sqlmap"))


def test_gov_basic_passive_violation_is_raised_for_bad_profile(monkeypatch) -> None:
    """If 02's gov/basic cell ever leaked an active tool, the resolver raises."""
    import src.scanning.resolver as resolver_mod
    from src.scans.domain.value_objects.tool_invocation import ToolInvocation

    bad = (ToolInvocation(ToolId.SQLMAP, ()),)  # sqlmap is NOT passive
    monkeypatch.setattr(resolver_mod, "resolve_toolset", lambda *a, **k: bad)

    expect(lambda: resolver_mod.resolve_tools(is_gov=True, level=ScanLevel.BASICO)).to(
        raise_error(PassiveProfileViolation)
    )
