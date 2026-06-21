"""``ListScanFindings`` — ``GET /scans/{id}/findings`` (12-api §"Lectura").

Findings of one scan, ordered by **severity desc** then uuid, cursor-paginated.
Access control (404 for private non-owner) is enforced upstream by
``require_scan_access``; this use case just reads, sorts and slices.

Findings belong to a single bounded scan, so the repo's ``list_for_scan`` returns
them all and we sort + keyset-slice in memory using the stable ``(severity, uuid)``
cursor from ``common.presentation.pagination`` (no parallel codec).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.entities.common.pagination import Page
from src.common.domain.interfaces.use_case import UseCase
from src.common.presentation.pagination import (
    CursorPage,
    decode_severity_cursor,
    encode_severity_cursor,
    severity_rank,
)
from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.repositories.finding import FindingRepository


def _sort_key(finding: FindingRecord) -> tuple[int, str]:
    # severity DESC == rank ASC (critical=0). uuid as a stable tie-breaker.
    return (severity_rank(finding.severity), str(finding.uuid))


@dataclass
class ListScanFindings(UseCase):
    scan_id: UUID
    finding_repository: FindingRepository
    limit: int = 25
    cursor: str | None = None

    async def execute(self, *args, **kwargs) -> Page:
        findings = await self.finding_repository.list_for_scan(self.scan_id)
        findings.sort(key=_sort_key)

        if self.cursor is not None:
            cursor_sev, cursor_uuid = decode_severity_cursor(self.cursor)
            cursor_key = (severity_rank(cursor_sev), str(cursor_uuid))
            findings = [f for f in findings if _sort_key(f) > cursor_key]

        window = findings[: self.limit + 1]
        return CursorPage.build(
            window,
            limit=self.limit,
            cursor_of=lambda f: encode_severity_cursor(f.severity, f.uuid),
        )
