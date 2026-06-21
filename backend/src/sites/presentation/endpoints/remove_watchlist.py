"""``DELETE /watchlist/{id}`` — remove a watched site (12-api §"Watchlist").

``{id}`` is the watchlist-row uuid; ``require_watchlist_owner`` resolves it (404
otherwise) and yields its ``site_id`` for the removal.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.ownership import require_watchlist_owner
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.sites.application.use_cases.remove_from_watchlist import RemoveFromWatchlist
from src.sites.domain.models.watchlist import WatchlistEntry


async def remove_watchlist(
    domain_context: DomainContextDep,
    entry: Annotated[WatchlistEntry, Depends(require_watchlist_owner)],
    user: Annotated[User, Depends(get_authenticated_user)],
) -> ApiJSONResponse:
    await RemoveFromWatchlist(
        user_id=user.uuid,
        site_id=entry.site_id,
        watchlist_repository=domain_context.watchlist_repository,
    ).execute()

    return ApiJSONResponse(
        content={"removed": True, "id": str(entry.uuid)},
        status_code=status.HTTP_200_OK,
    )
