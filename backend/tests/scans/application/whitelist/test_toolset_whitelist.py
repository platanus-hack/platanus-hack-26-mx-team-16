"""Whitelist policy tests (02-attack-levels §3-§8) — pure, DB-less.

Covers: whitelist shape, gov/basic byte-identity legal floor, allow-list negative,
cumulative ladder, hexstrike gating, demo orthogonality, and immutability.
"""

from __future__ import annotations

import pytest
from expects import be, contain, equal, expect, raise_error

from src.common.domain.enums.scans import ScanLevel
from src.scans.application.whitelist.resolve_toolset import resolve_toolset
from src.scans.application.whitelist.toolset_whitelist import (
    DEMO_PROFILE,
    HEXSTRIKE_INVOCATION,
    TOOLSET_WHITELIST,
)
from src.scans.domain.enums.tool_id import ToolId
from src.scans.domain.value_objects.tool_invocation import ToolInvocation

_ALL_LEVELS = (ScanLevel.BASICO, ScanLevel.INTERMEDIO, ScanLevel.AVANZADO)
_GOV_FLAGS = (True, False)


# --- Whitelist shape -------------------------------------------------------


def test_whitelist_has_exactly_the_six_cells() -> None:
    expect(set(TOOLSET_WHITELIST.keys())).to(
        equal({(g, lvl) for g in _GOV_FLAGS for lvl in _ALL_LEVELS})
    )


@pytest.mark.parametrize("g", _GOV_FLAGS)
@pytest.mark.parametrize("lvl", _ALL_LEVELS)
def test_every_cell_is_a_tuple_of_frozen_invocations(g: bool, lvl: ScanLevel) -> None:
    cell = TOOLSET_WHITELIST[(g, lvl)]
    expect(isinstance(cell, tuple)).to(be(True))
    for ti in cell:
        expect(isinstance(ti, ToolInvocation)).to(be(True))
        expect(isinstance(ti.flags, tuple)).to(be(True))


# --- Gov/basic legal floor: byte-identity guard (§10.1) --------------------


def test_gov_basic_is_exactly_the_canonical_legal_floor() -> None:
    expected = (
        ToolInvocation(ToolId.TESTSSL, ("--root",)),
        ToolInvocation(ToolId.SECURITY_HEADERS, ("--root",)),
        ToolInvocation(ToolId.WHATWEB, ("--root",)),
        ToolInvocation(
            ToolId.NUCLEI,
            (
                "-tags",
                "exposures,misconfiguration,ssl,tech,dns",
                "-etags",
                "intrusive,dos,fuzzing,network",
                "-no-spider",
            ),
        ),
    )
    expect(resolve_toolset(True, ScanLevel.BASICO)).to(equal(expected))


# --- Allow-list negative (§10.2) -------------------------------------------


def test_gov_basic_excludes_all_active_tools() -> None:
    tools = {ti.tool for ti in resolve_toolset(True, ScanLevel.BASICO)}
    forbidden = {
        ToolId.ZAP_BASELINE,
        ToolId.ZAP_FULL_ACTIVE,
        ToolId.KATANA,
        ToolId.FFUF,
        ToolId.SQLMAP,
        ToolId.NIKTO,
        ToolId.HEXSTRIKE,
    }
    expect(tools & forbidden).to(equal(set()))


def test_gov_cells_never_contain_spider_or_katana_crawlers() -> None:
    # ZAP spider + katana do not honor robots.txt -> illegal for passive gov.
    for lvl in (ScanLevel.BASICO,):
        tools = {ti.tool for ti in TOOLSET_WHITELIST[(True, lvl)]}
        expect(ToolId.KATANA in tools).to(be(False))


# --- Cumulative ladder (§10.3) ---------------------------------------------


@pytest.mark.parametrize("g", _GOV_FLAGS)
def test_levels_are_cumulative(g: bool) -> None:
    basic = set(resolve_toolset(g, ScanLevel.BASICO))
    inter = set(resolve_toolset(g, ScanLevel.INTERMEDIO))
    adv = set(resolve_toolset(g, ScanLevel.AVANZADO))
    expect(basic.issubset(inter)).to(be(True))
    expect(inter.issubset(adv)).to(be(True))


def test_advanced_non_gov_contains_advanced_delta() -> None:
    tools = {ti.tool for ti in resolve_toolset(False, ScanLevel.AVANZADO)}
    expect(tools).to(contain(ToolId.ZAP_FULL_ACTIVE))
    expect(tools).to(contain(ToolId.SQLMAP))


# --- hexstrike gating (§10.4) ----------------------------------------------


def test_advanced_without_hexstrike_ok_has_no_hexstrike() -> None:
    resolved = resolve_toolset(False, ScanLevel.AVANZADO, hexstrike_ok=False)
    expect(HEXSTRIKE_INVOCATION in resolved).to(be(False))


def test_advanced_with_hexstrike_ok_appends_hexstrike() -> None:
    resolved = resolve_toolset(False, ScanLevel.AVANZADO, hexstrike_ok=True)
    expect(resolved).to(contain(HEXSTRIKE_INVOCATION))
    # fallback battery still present alongside hexstrike
    tools = {ti.tool for ti in resolved}
    expect(tools).to(contain(ToolId.ZAP_FULL_ACTIVE))


@pytest.mark.parametrize("lvl", (ScanLevel.BASICO, ScanLevel.INTERMEDIO))
def test_hexstrike_ok_does_nothing_below_advanced(lvl: ScanLevel) -> None:
    resolved = resolve_toolset(False, lvl, hexstrike_ok=True)
    expect(HEXSTRIKE_INVOCATION in resolved).to(be(False))


def test_hexstrike_absent_from_every_cell_by_default() -> None:
    for cell in TOOLSET_WHITELIST.values():
        expect(HEXSTRIKE_INVOCATION in cell).to(be(False))


# --- Demo orthogonal to level + is_gov (§10.5) -----------------------------


@pytest.mark.parametrize("g", _GOV_FLAGS)
@pytest.mark.parametrize("lvl", _ALL_LEVELS)
def test_demo_ignores_level_and_is_gov(g: bool, lvl: ScanLevel) -> None:
    expect(resolve_toolset(g, lvl, demo=True)).to(equal(DEMO_PROFILE))


def test_demo_is_not_a_whitelist_key() -> None:
    # DEMO_PROFILE is not a 4th level; it has no (is_gov, "demo") cell.
    keys_levels = {lvl for (_g, lvl) in TOOLSET_WHITELIST.keys()}
    expect(keys_levels).to(equal(set(_ALL_LEVELS)))


# --- Immutability (§10.6) --------------------------------------------------


def test_whitelist_mapping_is_immutable() -> None:
    # ``TOOLSET_WHITELIST`` is a ``MappingProxyType`` (read-only view). Item
    # assignment via the subscript protocol raises ``TypeError`` ("mappingproxy
    # object does not support item assignment"). Note: calling ``__setitem__``
    # directly would instead raise ``AttributeError`` (the proxy does not expose
    # that dunder at all), so we assert the real, idiomatic mutation path.
    def _mutate() -> None:
        TOOLSET_WHITELIST[(True, ScanLevel.BASICO)] = ()

    expect(_mutate).to(raise_error(TypeError))


def test_tool_invocation_is_frozen() -> None:
    ti = ToolInvocation(ToolId.NUCLEI, ())
    expect(lambda: setattr(ti, "tool", ToolId.SQLMAP)).to(raise_error(Exception))
