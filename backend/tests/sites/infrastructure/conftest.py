"""DB isolation for sites/scans infrastructure tests.

These tests drive the real repositories, whose ``atomic_transaction`` COMMITs —
so rows persist across tests in the session-scoped schema. Without cleanup, the
gov leaderboard / change-detection assertions (which count rows globally) leak
into each other. This autouse fixture truncates the scan-engine tables after
each test so every case starts from an empty, deterministic state.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

# Order matters only for readability; TRUNCATE ... CASCADE handles FK deps.
_TABLES = (
    "alerts",
    "findings",
    "scan_events",
    "public_reports",
    "agentic_surface",
    "watchlist",
    "scans",
    "sites",
    "users",
)


async def _truncate(session):
    await session.rollback()
    await session.execute(
        text(f"TRUNCATE TABLE {', '.join(_TABLES)} RESTART IDENTITY CASCADE")
    )
    await session.commit()


@pytest.fixture(autouse=True)
async def _clean_scan_engine_tables(async_session):
    # Truncate BEFORE (defend against rows committed by other test files in this
    # session) and AFTER (leave a clean slate) each test.
    await _truncate(async_session)
    yield
    await _truncate(async_session)
