"""hexstrike flag + healthcheck (plan §10: test_hexstrike_flag) — spec §10."""

from __future__ import annotations

from expects import be_false, be_true, contain, expect

from src.common.domain.enums.scans import ScanLevel
from src.scanning import health as health_mod
from src.scanning.health import hexstrike_available
from src.scanning.resolver import resolve_tools


def _ids(invocations) -> set[str]:
    return {str(i.tool) for i in invocations}


async def test_hexstrike_absent_when_flag_off(monkeypatch) -> None:
    monkeypatch.setattr(health_mod.settings, "ENABLE_HEXSTRIKE", False, raising=False)
    available = await hexstrike_available()
    expect(available).to(be_false)
    # resolver fed the (false) availability -> tool absent from advanced.
    adv = _ids(resolve_tools(is_gov=False, level=ScanLevel.AVANZADO, hexstrike_ok=available))
    expect(adv).not_to(contain("hexstrike"))


async def test_hexstrike_absent_when_flag_on_but_healthcheck_ko(monkeypatch) -> None:
    monkeypatch.setattr(health_mod.settings, "ENABLE_HEXSTRIKE", True, raising=False)

    async def fake_check(**_kwargs) -> bool:
        return False

    monkeypatch.setattr(health_mod, "check_hexstrike", fake_check)

    available = await hexstrike_available()
    expect(available).to(be_false)
    adv = _ids(resolve_tools(is_gov=False, level=ScanLevel.AVANZADO, hexstrike_ok=available))
    # falls back to guaranteed battery (ZAP full + nuclei fuzzing + sqlmap).
    expect(adv).not_to(contain("hexstrike"))
    expect(adv).to(contain("zap_full_active"))
    expect(adv).to(contain("sqlmap"))


async def test_hexstrike_present_when_flag_on_and_healthcheck_ok(monkeypatch) -> None:
    monkeypatch.setattr(health_mod.settings, "ENABLE_HEXSTRIKE", True, raising=False)

    async def fake_check(**_kwargs) -> bool:
        return True

    monkeypatch.setattr(health_mod, "check_hexstrike", fake_check)

    available = await hexstrike_available()
    expect(available).to(be_true)
    adv = _ids(resolve_tools(is_gov=False, level=ScanLevel.AVANZADO, hexstrike_ok=available))
    expect(adv).to(contain("hexstrike"))


async def test_check_hexstrike_returns_false_on_connection_error(monkeypatch) -> None:
    import asyncio

    async def boom(*_a, **_k):
        raise OSError("connection refused")

    monkeypatch.setattr(asyncio, "open_connection", boom)
    result = await health_mod.check_hexstrike(host="nope", port=8888, timeout_s=0.1)
    expect(result).to(be_false)
