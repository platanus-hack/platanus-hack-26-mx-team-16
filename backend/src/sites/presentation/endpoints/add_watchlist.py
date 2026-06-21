"""``POST /watchlist {url, monitor}`` — add a site, return the created row (12-api)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.sites.application.use_cases.add_to_watchlist import AddToWatchlist
from src.sites.presentation.presenters.watchlist_row import WatchlistRowPresenter
from src.sites.presentation.requests.add_watchlist import AddWatchlistRequest


async def add_watchlist(
    request: AddWatchlistRequest,
    domain_context: DomainContextDep,
    user: Annotated[User, Depends(get_authenticated_user)],
) -> ApiJSONResponse:
    row = await AddToWatchlist(
        user_id=user.uuid,
        url=request.url,
        monitor=request.monitor,
        site_repository=domain_context.site_repository,
        watchlist_repository=domain_context.watchlist_repository,
        scan_repository=domain_context.scan_repository,
    ).execute()

    return ApiJSONResponse(
        content=WatchlistRowPresenter(row).to_dict,
        status_code=status.HTTP_201_CREATED,
    )
