from __future__ import annotations

import urllib.robotparser
from urllib.parse import urljoin, urlparse

from src.common.settings import settings
from src.scans.domain.services.robots_policy import RobotsPolicy


class UrllibRobotsPolicy(RobotsPolicy):
    """robots.txt enforcement backed by the stdlib ``urllib.robotparser``.

    The final fetch/egress mechanics are governed by 04-scanning-engine; this impl
    keeps the policy logic inside the ``scans`` module so it can be unit-tested and
    wired via constructor injection in ``scans_wiring`` (the live bus path).
    """

    async def is_allowed(self, url: str) -> bool:
        base = urlparse(url)
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(urljoin(f"{base.scheme}://{base.netloc}", "/robots.txt"))
        parser.read()
        return parser.can_fetch(settings.SCANNER_USER_AGENT, url)
