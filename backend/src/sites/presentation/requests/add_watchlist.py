"""``POST /watchlist`` request body (12-api §"Watchlist")."""

from __future__ import annotations

from src.common.domain.entities.common.requests import CamelCaseRequest


class AddWatchlistRequest(CamelCaseRequest):
    url: str
    monitor: bool = True
