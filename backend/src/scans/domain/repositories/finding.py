"""``FindingRepository`` ABC (06-data-model §3.3, §4)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.scans.domain.models.finding import FindingRecord


class FindingRepository(ABC):
    @abstractmethod
    async def upsert(self, finding: FindingRecord) -> FindingRecord:
        """UPSERT by ``(site_id, dedupe_key)`` (§4): insert a new finding or
        refresh ``last_seen``/scan_id/details of an existing one without
        duplicating. ``first_seen`` is preserved across re-scans."""
        raise NotImplementedError

    @abstractmethod
    async def list_for_scan(self, scan_id: UUID) -> list[FindingRecord]:
        raise NotImplementedError

    @abstractmethod
    async def list_for_site(self, site_id: UUID) -> list[FindingRecord]:
        raise NotImplementedError

    @abstractmethod
    async def mark_fixed_absent(self, site_id: UUID, present_keys: list[str]) -> int:
        """Flip site findings whose ``dedupe_key`` is not in ``present_keys`` to
        ``status='fixed'`` (a finding that stops reappearing is resolved, §3.3).
        Returns the number of rows updated."""
        raise NotImplementedError

    @abstractmethod
    async def criticals_first_seen_in(self, scan_id: UUID) -> list[FindingRecord]:
        """Return the ``critical`` findings of ``scan_id`` that are **new at the
        site level** — i.e. whose ``first_seen`` equals this scan's findings'
        ``first_seen`` (no earlier occurrence). Used by the monitoring alert
        engine to fire only on genuinely new criticals (08-ranking-watchlists
        §4.3); a pre-existing critical (older ``first_seen``) is excluded."""
        raise NotImplementedError
