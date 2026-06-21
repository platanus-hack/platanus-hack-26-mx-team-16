"""Bus wiring for the scans module (12-api enqueue path).

Registers the ``RunScanCommand`` handler so ``EnqueueScan`` can dispatch it with
``run_async=True`` (the ``MemoryCommandBus`` only enqueues commands that have a
registered handler). The handler itself is a Phase-1 placeholder — 05-agent-team
swaps in the real scan orchestration.
"""

from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.scans.application.commands.run_scan import RunScanCommand
from src.scans.application.commands.run_scan_handler import RunScanHandler
from src.sites.application.commands.seed_gov import SeedGovCommand, SeedGovHandler


def scans_wiring(
    domain: DomainContext,
    bus: BusContext,
):
    #  C O M M A N D S
    bus.command_bus.subscribe(
        command=RunScanCommand,
        handler=RunScanHandler(),
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
