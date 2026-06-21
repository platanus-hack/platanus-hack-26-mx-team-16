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


def scans_wiring(
    _domain: DomainContext,
    bus: BusContext,
):
    #  C O M M A N D S
    bus.command_bus.subscribe(
        command=RunScanCommand,
        handler=RunScanHandler(),
    )
