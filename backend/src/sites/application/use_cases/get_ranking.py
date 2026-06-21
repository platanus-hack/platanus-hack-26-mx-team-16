"""``GetRanking`` — ``GET /ranking?country=mx`` (12-api §"Lectura"; 08-ranking).

Global gov leaderboard, worst-first. The ordering contract
(``overall_grade ASC, penalty_raw DESC``) is owned by 07-scoring
(``LEADERBOARD_ORDER``) and applied by the repo's ``leaderboard`` query, which is
already filtered to ``sites.is_gov`` and each site's latest scan — i.e. only the
automatic public gov surface, never a private scan. This use case wraps the
repo's worst-first window in a cursor ``Page`` for the API envelope.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.common.domain.entities.common.pagination import Page
from src.common.domain.interfaces.use_case import UseCase
from src.scans.domain.repositories.scan import ScanRepository


@dataclass
class GetRanking(UseCase):
    scan_repository: ScanRepository
    limit: int = 25
    cursor: str | None = None

    async def execute(self, *args, **kwargs) -> Page:
        scans = await self.scan_repository.leaderboard(
            limit=self.limit, cursor=self.cursor
        )
        # The leaderboard query does not yet emit a keyset cursor; expose the
        # worst-first window as a single page. (Cursor continuation is a 08 follow-up.)
        return Page(items=scans, next_cursor=None, limit=self.limit)
