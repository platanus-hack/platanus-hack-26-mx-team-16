"""``PUT /me/alerts {emailEnabled, slackWebhookUrl}`` — upsert prefs (12-api)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, status

from src.common.domain.models.user import User
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.session import get_authenticated_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.sites.application.use_cases.update_alert_prefs import UpdateAlertPrefs
from src.sites.presentation.presenters.alert_prefs import AlertPrefsPresenter
from src.sites.presentation.requests.alert_prefs import AlertPrefsRequest


async def put_alerts(
    request: AlertPrefsRequest,
    domain_context: DomainContextDep,
    user: Annotated[User, Depends(get_authenticated_user)],
) -> ApiJSONResponse:
    prefs = await UpdateAlertPrefs(
        user_id=user.uuid,
        notification_prefs_repository=domain_context.notification_prefs_repository,
        email_enabled=request.email_enabled,
        slack_webhook_url=request.slack_webhook_url,
    ).execute()

    return ApiJSONResponse(
        content=AlertPrefsPresenter(prefs).to_dict,
        status_code=status.HTTP_200_OK,
    )
