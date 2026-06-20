"""``AgenticSurfaceRepository`` ABC (06-data-model §3.4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.scans.domain.models.agentic_surface import AgenticSurface


class AgenticSurfaceRepository(ABC):
    @abstractmethod
    async def add(self, surface: AgenticSurface) -> AgenticSurface:
        raise NotImplementedError

    @abstractmethod
    async def list_for_scan(self, scan_id: UUID) -> list[AgenticSurface]:
        raise NotImplementedError
