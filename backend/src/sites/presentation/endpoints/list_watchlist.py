"""``GET /watchlist`` — the user's watched sites (12-api §"Watchlist")."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.sites.application.use_cases.list_watchlist import ListWatchlist
from src.sites.presentation.presenters.watchlist_row import WatchlistRowPresenter


async def list_watchlist(
    domain_context: DomainContextDep,
    user: Annotated[User, Depends(get_authenticated_user)],
) -> ApiJSONResponse:
    rows = await ListWatchlist(
        user_id=user.uuid,
        watchlist_repository=domain_context.watchlist_repository,
        site_repository=domain_context.site_repository,
        scan_repository=domain_context.scan_repository,
    ).execute()

    return ApiJSONResponse(
        content=[WatchlistRowPresenter(row).to_dict for row in rows],
        status_code=status.HTTP_200_OK,
    )
