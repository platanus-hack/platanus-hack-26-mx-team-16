"""API-surface domain errors for the scans/public-report endpoints (12-api §4, §5.1).

All extend ``DomainError`` so the global ``domain_error_handler`` registered in
``config/main.py`` serializes them to the single error envelope
``{"errors": [{"code", "message"}], "validation": null, "timestamp": "..."}``
with the right HTTP status — no new handler is added.

``ScanNotFoundError`` is raised both for a genuinely-absent scan **and** for a
private scan the caller may not see: returning **404 (never 403)** is a hard
anti-IDOR rule (spec §"AuthZ por endpoint") — the API must never confirm the
existence of a private resource to a non-owner.
"""

from __future__ import annotations

from typing import Any

from src.common.domain.constants import status
from src.common.domain.exceptions._base import DomainError


class ScanNotFoundError(DomainError):
    """The scan does not exist, or the caller may not access this private scan.

    404 (not 403) on purpose: the existence of a private scan is never leaked to
    a non-owner (spec §"AuthZ por endpoint — evitar IDOR").
    """

    def __init__(self, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="scan.NotFound",
            message="Scan not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            context=context,
        )


class PublicReportNotFoundError(DomainError):
    """No ``public_reports`` row matches the token (spec §"Reporte público")."""

    def __init__(self, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="publicReport.NotFound",
            message="This report link is invalid.",
            status_code=status.HTTP_404_NOT_FOUND,
            context=context,
        )


class PublicReportGoneError(DomainError):
    """The token is expired or revoked → 410 Gone (spec §"Reporte público").

    Distinct from 404 so the frontend can show the "Este enlace expiró" copy.
    """

    def __init__(self, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            code="publicReport.Gone",
            message="This report link has expired.",
            status_code=status.HTTP_410_GONE,
            context=context,
        )
