"""``AlertRepository`` ABC (06-data-model §3.6)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.scans.domain.models.alert import Alert


class AlertRepository(ABC):
    @abstractmethod
    async def log(self, alert: Alert) -> Alert:
        """Append a sent-notification record (the alert log, §3.6)."""
        raise NotImplementedError

    @abstractmethod
    async def list_for_user(self, user_id: UUID) -> list[Alert]:
        raise NotImplementedError
