"""Phase-1 placeholder handler for :class:`RunScanCommand`.

``EnqueueScan`` dispatches ``RunScanCommand`` with ``run_async=True``. The
``MemoryCommandBus`` requires the command to be *registered* before it will hand
it to the ``SaqCommandEnqueuer`` (the registration is what both the API process —
to enqueue — and the SAQ worker — to execute — share). The real orchestration
(Opus + Sonnet + scanners) is owned by 05-agent-team and will replace this
handler's body; until then it only acknowledges the job so the enqueue path
(``POST /scans`` → 201/200) works end to end without a 500.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.common.application.logging import get_logger
from src.common.domain.buses.commands import CommandHandler
from src.scans.application.commands.run_scan import RunScanCommand

logger = get_logger(__name__)


@dataclass
class RunScanHandler(CommandHandler[RunScanCommand]):
    """Acknowledges an enqueued scan. Real execution lands with 05-agent-team."""

    async def execute(self, command: RunScanCommand) -> None:
        logger.info("run_scan.enqueued", scan_id=str(command.scan_id))
