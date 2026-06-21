"""``LegalRobotsPolicy`` — concrete impl of the 01 ``RobotsPolicy`` Protocol.

01 exposes two robots contracts: the ``RobotsPolicy`` *Protocol* in
``common/legal/robots.py`` (``user_agent`` / ``is_allowed(path)`` /
``filter_allowed(paths)``) and the async ABC in
``scans/domain/services/robots_policy.py`` with the ``UrllibRobotsPolicy`` impl.

This module does NOT re-implement robots parsing: it REUSES ``UrllibRobotsPolicy``
(the stdlib ``urllib.robotparser`` impl from 02) and adapts it to the synchronous
legal Protocol the worker / use cases / invariant tests depend on. ``robots.txt``
is fetched once with ``SCANNER_USER_AGENT``; ``Disallow`` paths are excluded
before any request. Missing ``robots.txt`` -> all allowed; unreachable -> fail-safe
to root-only for the passive profile.
"""

from __future__ import annotations

import urllib.robotparser
from collections.abc import Iterable
from urllib.parse import urljoin, urlparse

from src.common.application.logging import get_logger
from src.common.domain.legal.constants import SCANNER_USER_AGENT

logger = get_logger()


class LegalRobotsPolicy:
    """Synchronous ``RobotsPolicy`` Protocol impl (spec §5, plan §3.6).

    Fetches/parses ``robots.txt`` for ``base_url``'s host once at construction via
    ``from_url`` (or accepts a pre-built parser for tests). Evaluates rules against
    the identifiable ``SCANNER_USER_AGENT``. Satisfies the
    ``common.legal.robots.RobotsPolicy`` Protocol structurally.
    """

    __slots__ = ("_base", "_fail_safe_root_only", "_parser")

    def __init__(
        self,
        base_url: str,
        *,
        parser: urllib.robotparser.RobotFileParser | None = None,
        fail_safe_root_only: bool = True,
    ) -> None:
        parsed = urlparse(base_url)
        self._base = f"{parsed.scheme}://{parsed.netloc}"
        self._fail_safe_root_only = fail_safe_root_only
        self._parser = parser if parser is not None else self._load()

    def _load(self) -> urllib.robotparser.RobotFileParser:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(urljoin(self._base, "/robots.txt"))
        try:
            parser.read()
        except Exception:  # noqa: BLE001 - unreachable robots -> fail-safe (plan §3.6)
            logger.warning("robots.unreachable", extra={"base": self._base})
            # Mark as "errored": can_fetch() will then return False for non-root,
            # honoring the fail-safe-to-root-only contract for the passive profile.
            parser.disallow_all = self._fail_safe_root_only
        return parser

    @property
    def user_agent(self) -> str:
        """The UA the policy matched rules against (``SCANNER_USER_AGENT``)."""
        return SCANNER_USER_AGENT

    def _abs(self, path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        return urljoin(self._base, path)

    def is_allowed(self, path: str) -> bool:
        """True if ``path`` is requestable (not under a matching ``Disallow``)."""
        return self._parser.can_fetch(SCANNER_USER_AGENT, self._abs(path))

    def filter_allowed(self, paths: Iterable[str]) -> list[str]:
        """Return the subset of ``paths`` that may be requested (drops Disallow)."""
        return [p for p in paths if self.is_allowed(p)]
