from __future__ import annotations

from abc import ABC, abstractmethod


class RobotsPolicy(ABC):
    """Honors robots.txt before any OWASP-web request (spec §5).

    Mandatory on the gov/passive path (part of the legal definition of "passive")
    and the default for the basic level's light recon. The User-Agent it evaluates
    against is the identifiable ``Owliver-Scanner/1.0`` (settings.SCANNER_USER_AGENT;
    UA + rate-limit policy detail is owned by 01-legal-ethics).
    """

    @abstractmethod
    async def is_allowed(self, url: str) -> bool:
        """True if the host's robots.txt allows Owliver-Scanner/1.0 to access url."""
        raise NotImplementedError
