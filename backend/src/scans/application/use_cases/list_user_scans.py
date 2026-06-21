"""``ListUserScans`` — ``GET /scans`` (12-api). Cursor-paginated, newest first."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.common.domain.entities.common.pagination import Page
from src.common.domain.interfaces.use_case import UseCase
from src.common.presentation.pagination import CursorPage, encode_cursor
from src.scans.domain.repositories.scan import ScanRepository


@dataclass
class ListUserScans(UseCase):
    user_id: UUID
    scan_repository: ScanRepository
    status: str | None = None
    site_id: UUID | None = None
    limit: int = 25
    cursor: str | None = None

    async def execute(self, *args, **kwargs) -> Page:
        rows = await self.scan_repository.find_for_user(
            self.user_id,
            status=self.status,
            site_id=self.site_id,
            limit=self.limit,
            cursor=self.cursor,
        )
        return CursorPage.build(
            rows,
            limit=self.limit,
            cursor_of=lambda scan: (
                encode_cursor(scan.created_at, scan.uuid) if scan.created_at else None
            ),
        )
