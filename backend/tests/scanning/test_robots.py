"""LegalRobotsPolicy (plan §10: test_robots_policy) — honors robots.txt (spec §5)."""

from __future__ import annotations

import urllib.robotparser

from expects import be_false, be_true, contain, equal, expect

from src.common.domain.legal.constants import SCANNER_USER_AGENT
from src.scanning.robots import LegalRobotsPolicy

_ROBOTS = """User-agent: *
Disallow: /private
Allow: /
"""


def _policy_with(robots_txt: str) -> LegalRobotsPolicy:
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(robots_txt.splitlines())
    return LegalRobotsPolicy("https://example.gob.mx", parser=parser)


def test_disallow_paths_excluded() -> None:
    policy = _policy_with(_ROBOTS)
    expect(policy.is_allowed("/private/secret")).to(be_false)
    expect(policy.is_allowed("/public/page")).to(be_true)


def test_filter_allowed_drops_disallowed() -> None:
    policy = _policy_with(_ROBOTS)
    allowed = policy.filter_allowed(["/public/a", "/private/b", "/c"])
    expect(allowed).to(contain("/public/a"))
    expect(allowed).to(contain("/c"))
    expect(allowed).not_to(contain("/private/b"))


def test_user_agent_is_scanner_ua() -> None:
    policy = _policy_with(_ROBOTS)
    expect(policy.user_agent).to(equal(SCANNER_USER_AGENT))


def test_missing_robots_allows_all() -> None:
    # An empty/absent robots.txt -> everything allowed.
    policy = _policy_with("")
    expect(policy.is_allowed("/anything")).to(be_true)


def test_satisfies_legal_protocol() -> None:
    from src.common.domain.legal.robots import RobotsPolicy

    policy = _policy_with(_ROBOTS)
    # runtime_checkable Protocol — structural conformance.
    expect(isinstance(policy, RobotsPolicy)).to(be_true)
