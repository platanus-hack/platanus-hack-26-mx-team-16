"""``PATCH /watchlist/{id}`` request body (12-api §"Watchlist")."""

from __future__ import annotations

from src.common.domain.entities.common.requests import CamelCaseRequest


class ToggleWatchlistRequest(CamelCaseRequest):
    monitor: bool
