"""``RobotsPolicy`` contract (spec §3). Implementation belongs to 04.

The gov passive scan MUST honor ``robots.txt``: parse it (with
``SCANNER_USER_AGENT``) **before any request** and exclude ``Disallow`` paths.
ZAP spider and katana do not respect robots, so they are disabled for gov; this
policy is the defense-in-depth that excludes disallowed paths regardless.

This module exposes only the Protocol — the concrete implementation (network
fetch + parsing) lives in 04-scanning-engine. Keeping the contract here lets the
worker, use cases and the invariant test suite depend on the shape without a
layer dependency.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable


@runtime_checkable
class RobotsPolicy(Protocol):
    """Robots.txt gate evaluated before any outgoing scan request.

    Implementations fetch/parse ``robots.txt`` for the target host using
    ``SCANNER_USER_AGENT`` and answer whether a path may be requested. The policy
    is consulted by the worker (04) before issuing any tool request against gov.
    """

    @property
    def user_agent(self) -> str:
        """The User-Agent the policy matched rules against — ``SCANNER_USER_AGENT``."""
        ...

    def is_allowed(self, path: str) -> bool:
        """True if ``path`` is requestable (not under a matching ``Disallow``)."""
        ...

    def filter_allowed(self, paths: Iterable[str]) -> list[str]:
        """Return the subset of ``paths`` that may be requested.

        Convenience used by the worker to drop ``Disallow`` paths in one call
        before issuing any request.
        """
        ...
