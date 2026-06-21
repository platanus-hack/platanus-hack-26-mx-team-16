"""Robots/UA invariant (01-legal §2.5, §3) — pure contract.

Invariant: every outgoing scan request carries the identifiable
``SCANNER_USER_AGENT``; the ``RobotsPolicy`` contract excludes ``Disallow`` paths
before any request and matches rules against that same UA.

The concrete ``RobotsPolicy`` impl lives in 04; here a minimal fake proves the
contract shape the worker depends on, plus that the UA constant is the single
identifiable value.
"""

from __future__ import annotations

from collections.abc import Iterable

from expects import contain, equal, expect

from src.common.domain.legal.constants import SCANNER_USER_AGENT
from src.common.domain.legal.robots import RobotsPolicy


class _FakeRobotsPolicy:
    """Minimal in-memory robots policy honoring a ``Disallow`` set."""

    def __init__(self, disallow: set[str]) -> None:
        self._disallow = disallow

    @property
    def user_agent(self) -> str:
        return SCANNER_USER_AGENT

    def is_allowed(self, path: str) -> bool:
        return not any(path.startswith(d) for d in self._disallow)

    def filter_allowed(self, paths: Iterable[str]) -> list[str]:
        return [p for p in paths if self.is_allowed(p)]


def test_user_agent_is_identifiable() -> None:
    expect(SCANNER_USER_AGENT).to(equal("Owliver-Scanner/1.0 (+contacto)"))
    expect(SCANNER_USER_AGENT).to(contain("Owliver"))
    expect(SCANNER_USER_AGENT).to(contain("contacto"))


def test_fake_policy_satisfies_protocol() -> None:
    policy = _FakeRobotsPolicy(disallow={"/admin"})
    # runtime_checkable Protocol -> structural conformance.
    expect(isinstance(policy, RobotsPolicy)).to(equal(True))


def test_disallow_paths_excluded_before_request() -> None:
    policy = _FakeRobotsPolicy(disallow={"/admin", "/internal"})
    candidate = ["/", "/admin", "/about", "/internal/api", "/contact"]
    allowed = policy.filter_allowed(candidate)
    expect(allowed).to(equal(["/", "/about", "/contact"]))
    expect(allowed).not_to(contain("/admin"))
    expect(allowed).not_to(contain("/internal/api"))


def test_policy_matches_rules_against_scanner_ua() -> None:
    policy = _FakeRobotsPolicy(disallow=set())
    expect(policy.user_agent).to(equal(SCANNER_USER_AGENT))
