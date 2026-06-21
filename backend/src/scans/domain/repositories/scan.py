"""``ScanRepository`` ABC (06-data-model §3.2, §4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.scans.domain.models.scan import Scan


class ScanRepository(ABC):
    @abstractmethod
    async def find(self, scan_id: UUID) -> Scan | None:
        raise NotImplementedError

    @abstractmethod
    async def find_active(self, site_id: UUID, level: str) -> Scan | None:
        """Return the live scan for ``(site_id, level)`` with status in
        {queued, running}, if any — the idempotency partner of ``enqueue`` (§4)."""
        raise NotImplementedError

    @abstractmethod
    async def enqueue(
        self,
        site_id: UUID,
        level: str,
        *,
        visibility: str,
        requested_by: UUID | None = None,
        authorized: bool = False,
    ) -> Scan:
        """Idempotently create a ``queued`` scan. If an active scan for
        ``(site_id, level)`` already exists (partial unique index on status in
        {queued, running}), return the existing one instead of inserting (§4)."""
        raise NotImplementedError

    @abstractmethod
    async def persist(self, scan: Scan) -> Scan:
        """Upsert the full scan row, including Python-computed score columns."""
        raise NotImplementedError

    @abstractmethod
    async def update_progress(
        self,
        scan_id: UUID,
        *,
        progress: int | None = None,
        current_phase: str | None = None,
        tools_status: dict | None = None,
        coverage: list | None = None,
        status: str | None = None,
        error: str | None = None,
    ) -> None:
        """Partial observability update for the live-view (§3.2)."""
        raise NotImplementedError

    @abstractmethod
    async def leaderboard(self, *, limit: int = 50, cursor: str | None = None) -> list[Scan]:
        """Gov sites ranked worst-first: ``overall_grade ASC, penalty_raw DESC``,
        filtered to ``sites.is_gov`` (§4, 08-ranking-watchlists)."""
        raise NotImplementedError

    @abstractmethod
    async def find_for_user(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
        site_id: UUID | None = None,
        limit: int = 50,
        cursor: str | None = None,
    ) -> list[Scan]:
        """List scans requested by ``user_id`` (``GET /scans``, 12-api), newest
        first, optionally filtered by ``status``/``site_id``. Returns ``limit + 1``
        rows so the API can derive ``next_cursor`` (keyset on ``created_at, uuid``)."""
        raise NotImplementedError

    @abstractmethod
    async def previous_graded_scan(
        self, site_id: UUID, *, before: UUID
    ) -> Scan | None:
        """Most recent **terminal, graded** scan of ``site_id`` strictly older
        than the scan ``before`` (08-ranking-watchlists §4.3): ``status IN
        ('done','partial') AND overall_grade IS NOT NULL``, ordered newest-first.
        This is the comparison base for the grade-drop alert; ``None`` for the
        first scan of a site (no base ⇒ no drop alert)."""
        raise NotImplementedError
