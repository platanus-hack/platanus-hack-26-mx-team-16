"""DB isolation for scans infrastructure tests.

The repositories under test ``atomic_transaction``-COMMIT, so rows persist across
tests in the session-scoped schema. The change-detection / alert-log assertions
count rows, so leftover state from a prior test leaks in. This autouse fixture
truncates the scan-engine tables after each test for a deterministic empty start.
Mock-only tests (slack/email/pdf) are unaffected; the truncate is a harmless no-op.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

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
