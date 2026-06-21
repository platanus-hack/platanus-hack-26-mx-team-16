"""``PUT /me/alerts`` request body (12-api §"Alertas")."""

from __future__ import annotations

from src.common.domain.entities.common.requests import CamelCaseRequest


class AlertPrefsRequest(CamelCaseRequest):
    email_enabled: bool = True
    slack_webhook_url: str | None = None
