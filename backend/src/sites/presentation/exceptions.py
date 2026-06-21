"""API-surface domain errors for the sites/watchlist endpoints (12-api §4).

Extend ``DomainError`` so the global handler serializes them to the single error
envelope. ``WatchlistEntryNotFoundError`` is 404 (never 403) for both an absent
row and a row owned by another user — same anti-IDOR rule as scans.
"""

from __future__ import annotations

from typing import Any

from src.common.domain.constants import status
from src.common.domain.exceptions._base import DomainError


class SiteNotFoundError(DomainError):
    def __init__(self, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="site.NotFound",
            message="Site not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            context=context,
        )


class WatchlistEntryNotFoundError(DomainError):
    """The watchlist row does not exist or is not the caller's (404, not 403)."""

    def __init__(self, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="watchlist.NotFound",
            message="Watchlist entry not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            context=context,
        )
