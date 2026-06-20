"""``PublicReportRepository`` ABC (06-data-model §3.7)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.scans.domain.models.public_report import PublicReport


class PublicReportRepository(ABC):
    @abstractmethod
    async def create(
        self, scan_id: UUID, *, expires_at: datetime | None = None
    ) -> PublicReport:
        """Mint a shareable report with an opaque ``secrets.token_urlsafe(32)``
        token (UNIQUE, §4)."""
        raise NotImplementedError

    @abstractmethod
    async def find_by_token(self, token: str) -> PublicReport | None:
        """Lookup by token. Expiry/revocation handling (410) lives in 12-api;
        the repo returns the row regardless so the caller can decide."""
        raise NotImplementedError

    @abstractmethod
    async def revoke(self, token: str) -> None:
        raise NotImplementedError
