"""``GET /sites/{id}`` — latest scan + history (12-api §"Lectura").

Public/owner: public scans are visible to anyone; private scans of the site are
only included for the owner. Optional auth resolves the requester.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, status

from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.session import (
    get_optional_authenticated_user,
)
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.sites.application.use_cases.get_site_history import GetSiteHistory
from src.sites.presentation.presenters.site_history import SiteHistoryPresenter


async def get_site(
    site_id: UUID,
    domain_context: DomainContextDep,
    user: Annotated[User | None, Depends(get_optional_authenticated_user)],
) -> ApiJSONResponse:
    view = await GetSiteHistory(
        site_id=site_id,
        site_repository=domain_context.site_repository,
        scan_repository=domain_context.scan_repository,
        requester_id=user.uuid if user is not None else None,
    ).execute()

    return ApiJSONResponse(
        content=SiteHistoryPresenter(view).to_dict,
        status_code=status.HTTP_200_OK,
    )
