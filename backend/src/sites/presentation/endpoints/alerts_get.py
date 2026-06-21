"""``GET /me/alerts`` — the user's alert-channel prefs (12-api §"Alertas")."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.sites.application.use_cases.get_alert_prefs import GetAlertPrefs
from src.sites.presentation.presenters.alert_prefs import AlertPrefsPresenter


async def get_alerts(
    domain_context: DomainContextDep,
    user: Annotated[User, Depends(get_authenticated_user)],
) -> ApiJSONResponse:
    prefs = await GetAlertPrefs(
        user_id=user.uuid,
        notification_prefs_repository=domain_context.notification_prefs_repository,
    ).execute()

    return ApiJSONResponse(
        content=AlertPrefsPresenter(prefs).to_dict,
        status_code=status.HTTP_200_OK,
    )
