"""``GET /watchlist`` — the user's watched sites (12-api §"Watchlist")."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.sites.application.use_cases.list_watchlist import ListWatchlist
from src.sites.presentation.presenters.watchlist_item import WatchlistItemPresenter


async def list_watchlist(
    domain_context: DomainContextDep,
    user: Annotated[User, Depends(get_authenticated_user)],
) -> ApiJSONResponse:
    entries = await ListWatchlist(
        user_id=user.uuid,
        watchlist_repository=domain_context.watchlist_repository,
    ).execute()

    return ApiJSONResponse(
        content=[WatchlistItemPresenter(entry).to_dict for entry in entries],
        status_code=status.HTTP_200_OK,
    )
