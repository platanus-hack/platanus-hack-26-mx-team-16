"""Bus wiring for the scans module (12-api enqueue path + 05 worker flow).

Registers the ``RunScanCommand`` handler so ``EnqueueScan`` can dispatch it with
``run_async=True`` (the ``MemoryCommandBus`` only enqueues commands that have a
registered handler). 05-agent-team swaps the placeholder for the real
``RunScanHandler`` that runs the worker flow; it is wired with the domain repos
(06) + the command bus (for the CRON alert path, 08) here.
"""

from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.scans.application.commands.run_scan import RunScanCommand
from src.scans.application.commands.run_scan_handler import RunScanHandler
from src.scans.infrastructure.repositories.sql_alert import SQLAlertRepository
from src.sites.application.commands.seed_gov import SeedGovCommand, SeedGovHandler


def scans_wiring(
    domain: DomainContext,
    bus: BusContext,
):
    #  C O M M A N D S
    # The alert repository is not part of DomainContext; build it from the shared
    # session the domain repos already hold (one session per job, plan §3).
    alert_repository = SQLAlertRepository(session=domain.scan_repository.session)
    bus.command_bus.subscribe(
        command=RunScanCommand,
        handler=RunScanHandler(
            scan_repository=domain.scan_repository,
            finding_repository=domain.finding_repository,
            scan_event_repository=domain.scan_event_repository,
            site_repository=domain.site_repository,
            agentic_surface_repository=domain.agentic_surface_repository,
            command_bus=bus.command_bus,
            notification_prefs_repository=domain.notification_prefs_repository,
            user_repository=domain.user_repository,
            alert_repository=alert_repository,
        ),
    )
    # Gov-ranking seed job (08-ranking-watchlists §2.3) — inserts gov sites and
    # enqueues passive scans through the same idempotency as POST /scans.
    bus.command_bus.subscribe(
        command=SeedGovCommand,
        handler=SeedGovHandler(
            site_repository=domain.site_repository,
            scan_repository=domain.scan_repository,
            command_bus=bus.command_bus,
        ),
    )
