"""DB tests for ``SQLScanRepository.persist`` — the worker ``_finalize`` write.

Regression for the MissingGreenlet that aborted every scan at finalize: the
UPDATE flush fires ``onupdate=func.now()`` for ``updated_at`` (server-side), so
SQLAlchemy expires that attribute; ``build_scan`` -> ``Scan.model_validate``
then lazily reloaded it, triggering async IO outside a greenlet. ``persist``
must ``refresh`` the row inside the greenlet first. Requires docker postgres.
"""

from uuid import uuid4

from expects import be_none, equal, expect

from src.common.database.models.scans.scan import ScanORM
from src.common.database.models.sites.site import SiteORM
from src.scans.infrastructure.repositories.sql_scan import SQLScanRepository


async def _seed_site(session) -> SiteORM:
    site = SiteORM(
        uuid=uuid4(), url="https://x.gob.mx", hostname="x.gob.mx", is_gov=True
    )
    session.add(site)
    await session.flush()
    return site


async def _seed_running_scan(session, site_id) -> ScanORM:
    scan = ScanORM(
        uuid=uuid4(), site_id=site_id, level="basico", status="running",
        visibility="public", progress=10,
    )
    session.add(scan)
    await session.flush()
    return scan


async def test_persist_update_path_does_not_raise_missing_greenlet(async_session):
    """Finalizing an existing scan (the UPDATE branch) returns the terminal Scan
    without a MissingGreenlet and with ``updated_at`` populated."""
    site = await _seed_site(async_session)
    seeded = await _seed_running_scan(async_session, site.uuid)
    repo = SQLScanRepository(session=async_session)

    # Mirror WorkerFlow._finalize: load -> model_copy(terminal fields) -> persist.
    loaded = await repo.find(seeded.uuid)
    terminal = loaded.model_copy(
        update={
            "status": "done",
            "overall_grade": "C",
            "overall_score": 70,
            "web_score": 65,
            "agentic_score": 80,
            "progress": 100,
            "current_phase": "finalizado",
        }
    )

    persisted = await repo.persist(terminal)

    expect(persisted.status).to(equal("done"))
    expect(persisted.overall_grade).to(equal("C"))
    expect(persisted.progress).to(equal(100))
    # The bug left this expired -> lazy load -> MissingGreenlet. The refresh in
    # ``persist`` must populate it inside the greenlet.
    expect(persisted.updated_at).not_to(be_none)

    # And it survived to the DB: a fresh read reflects the terminal state.
    reread = await repo.find(seeded.uuid)
    expect(reread.status).to(equal("done"))
    expect(reread.overall_score).to(equal(70))
