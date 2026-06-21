"""``PATCH /watchlist/{id} {monitor}`` — toggle monitoring (12-api §"Watchlist").

``require_watchlist_owner`` resolves the row by its uuid (404 if absent/foreign).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.ownership import require_watchlist_owner
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.sites.application.use_cases.toggle_watchlist_monitor import (
    ToggleWatchlistMonitor,
)
from src.sites.domain.models.watchlist import WatchlistEntry
from src.sites.presentation.presenters.watchlist_item import WatchlistItemPresenter
from src.sites.presentation.requests.toggle_watchlist import ToggleWatchlistRequest


async def toggle_watchlist(
    request: ToggleWatchlistRequest,
    domain_context: DomainContextDep,
    entry: Annotated[WatchlistEntry, Depends(require_watchlist_owner)],
    user: Annotated[User, Depends(get_authenticated_user)],
) -> ApiJSONResponse:
    updated = await ToggleWatchlistMonitor(
        user_id=user.uuid,
        site_id=entry.site_id,
        monitor=request.monitor,
        watchlist_repository=domain_context.watchlist_repository,
    ).execute()

    return ApiJSONResponse(
        content=WatchlistItemPresenter(updated).to_dict,
        status_code=status.HTTP_200_OK,
    )
