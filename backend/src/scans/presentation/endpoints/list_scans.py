"""``GET /scans?status=&site_id=&limit=&cursor=`` — the user's scans (12-api)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query, status

from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.scans.application.use_cases.list_user_scans import ListUserScans
from src.scans.presentation.presenters.scan import ScanListItemPresenter


async def list_scans(
    domain_context: DomainContextDep,
    user: Annotated[User, Depends(get_authenticated_user)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    site_id: Annotated[UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query()] = None,
) -> ApiJSONResponse:
    page = await ListUserScans(
        user_id=user.uuid,
        scan_repository=domain_context.scan_repository,
        status=status_filter,
        site_id=site_id,
        limit=limit,
        cursor=cursor,
    ).execute()

    # The scans row only carries site_id, so resolve the hostname for the row
    # title from the sites table — once per DISTINCT site (a user's history
    # usually spans few sites) rather than per row.
    scans = page.items or []
    hosts: dict[UUID, str | None] = {}
    for sid in {scan.site_id for scan in scans}:
        site = await domain_context.site_repository.find(sid)
        hosts[sid] = site.hostname if site is not None else None

    page.items = [
        ScanListItemPresenter(scan, host=hosts.get(scan.site_id)).to_dict
        for scan in scans
    ]
    return ApiJSONResponse(content=page, status_code=status.HTTP_200_OK)
