"""robots.txt honoring (§10.7) and demo-vs-global-budget distinction (§10.8)."""

from __future__ import annotations

import urllib.robotparser
from unittest.mock import patch

from expects import be, be_above, equal, expect

from src.common.settings import settings
from src.scans.infrastructure.services.urllib_robots_policy import UrllibRobotsPolicy

# Bind the real class now, before any patching, so the stub can delegate to it.
_RealRobotFileParser = urllib.robotparser.RobotFileParser

_ROBOTS_TXT = """User-agent: *
Disallow: /private
Allow: /
"""


class _StubParser:
    """Mimics RobotFileParser but parses an in-memory robots.txt (no network)."""

    def set_url(self, url: str) -> None:  # noqa: ARG002
        return None

    def read(self) -> None:
        real = _RealRobotFileParser()
        real.parse(_ROBOTS_TXT.splitlines())
        self._delegate = real

    def can_fetch(self, useragent: str, url: str) -> bool:
        return self._delegate.can_fetch(useragent, url)


async def test_robots_disallows_private_path() -> None:
    with patch("urllib.robotparser.RobotFileParser", _StubParser):
        policy = UrllibRobotsPolicy()
        allowed = await policy.is_allowed("https://example.gob.mx/private/x")
    expect(allowed).to(be(False))


async def test_robots_allows_public_path() -> None:
    with patch("urllib.robotparser.RobotFileParser", _StubParser):
        policy = UrllibRobotsPolicy()
        allowed = await policy.is_allowed("https://example.gob.mx/index.html")
    expect(allowed).to(be(True))


# --- demo vs global budget never confused (§10.8) --------------------------


def test_demo_timeout_is_at_most_90_seconds() -> None:
    expect(settings.DEMO_PROFILE_TIMEOUT_SECONDS <= 90).to(be(True))


def test_demo_and_global_budgets_are_distinct() -> None:
    expect(settings.DEMO_PROFILE_TIMEOUT_SECONDS).not_to(
        equal(settings.SCAN_GLOBAL_BUDGET_SECONDS)
    )
    expect(settings.SCAN_GLOBAL_BUDGET_SECONDS).to(be_above(settings.DEMO_PROFILE_TIMEOUT_SECONDS))


def test_hexstrike_disabled_by_default() -> None:
    expect(settings.ENABLE_HEXSTRIKE).to(be(False))


def test_scanner_user_agent_is_identifiable() -> None:
    expect(settings.SCANNER_USER_AGENT.startswith("Owliver-Scanner/1.0")).to(be(True))
