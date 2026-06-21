"""``GET /ranking?country=mx`` — public gov leaderboard (12-api §"Lectura")."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query, status

from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.sites.application.use_cases.get_ranking import GetRanking
from src.sites.presentation.presenters.ranking_item import RankingItemPresenter


async def get_ranking(
    domain_context: DomainContextDep,
    country: Annotated[str, Query()] = "mx",
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
) -> ApiJSONResponse:
    # `country` is part of the public contract; today only `mx` (.gob.mx) is ranked.
    page = await GetRanking(
        scan_repository=domain_context.scan_repository,
        limit=limit,
        cursor=cursor,
    ).execute()

    page.apply_presenter(RankingItemPresenter)
    return ApiJSONResponse(content=page, status_code=status.HTTP_200_OK)
