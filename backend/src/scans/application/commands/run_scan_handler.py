"""``RunScanHandler`` — runs the real pentest worker flow (05-agent-team).

Replaces the Phase-1 placeholder body: it resolves the scan + site, builds the
per-scan dependencies (``CancelToken`` (04), ``ScanEventEmitter`` (10), a Redis
client) and delegates the whole choreography to :class:`WorkerFlow` (which glues
04 tools + 06 repos + 07 scoring + 10 events + 08 alerts).

The handler stays thin — all sequencing lives in ``WorkerFlow``. It is constructed
in ``scans_wiring`` with the domain repos + the command bus; the Redis client is
built lazily from settings inside ``execute`` (the bus wiring does not carry the
worker's Redis handle). It runs inside the SAQ worker process via
``handle_command`` (no new SAQ function — plan §3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.application.logging import get_logger
from src.common.domain.buses.commands import CommandBus, CommandHandler
from src.common.settings import settings
from src.scans.application.commands.run_scan import RunScanCommand
from src.scans.domain.repositories.agentic_surface import AgenticSurfaceRepository
from src.scans.domain.repositories.finding import FindingRepository
from src.scans.domain.repositories.scan import ScanRepository
from src.scans.domain.repositories.scan_event import ScanEventRepository
from src.sites.domain.repositories.site import SiteRepository

logger = get_logger(__name__)


@dataclass
class RunScanHandler(CommandHandler[RunScanCommand]):
    """Builds the worker deps and runs ``WorkerFlow.run`` for the scan.

    Repos are injected from ``DomainContext`` via ``scans_wiring``. The alert repos
    are optional so a partial wiring (or a test) still constructs; they enable the
    CRON-origin ``EvaluateSiteAlerts`` path (08).
    """

    scan_repository: ScanRepository | None = None
    finding_repository: FindingRepository | None = None
    scan_event_repository: ScanEventRepository | None = None
    site_repository: SiteRepository | None = None
    # 03-agentic-surface persists detected surfaces; optional so a partial wiring
    # (or a test) still constructs. When absent, agentic rows are simply not saved.
    agentic_surface_repository: AgenticSurfaceRepository | None = None
    command_bus: CommandBus | None = None
    # Optional alert repos (08) — supplied by full wiring; omitted in tests.
    notification_prefs_repository: Any | None = None
    user_repository: Any | None = None
    alert_repository: Any | None = None

    async def execute(self, command: RunScanCommand) -> None:
        scan_id = command.scan_id
        if self.scan_repository is None or self.site_repository is None:
            logger.warning("run_scan.unwired", scan_id=str(scan_id))
            return

        scan = await self.scan_repository.find(scan_id)
        if scan is None:
            logger.warning("run_scan.scan_not_found", scan_id=str(scan_id))
            return
        site = await self.site_repository.find(scan.site_id)
        if site is None:
            logger.warning("run_scan.site_not_found", scan_id=str(scan_id))
            return

        redis = self._build_redis()
        try:
            flow = self._build_flow(redis, scan_id)
            await flow.run(
                scan_id=scan_id,
                url=site.url,
                level=scan.level,
                is_gov=site.is_gov,
            )
        except Exception as exc:  # noqa: BLE001 - persist the error, close the stream
            logger.error("run_scan.failed", scan_id=str(scan_id), error=str(exc))
            await self._record_error(scan_id, redis, exc)
            raise
        finally:
            await self._close_redis(redis)

    # -- construction ----------------------------------------------------------

    def _build_redis(self) -> Any | None:
        try:
            from redis.asyncio import Redis  # noqa: PLC0415

            return Redis.from_url(
                settings.redis_url, decode_responses=True, encoding="utf-8"
            )
        except Exception:  # noqa: BLE001 - the flow tolerates a None redis
            logger.warning("run_scan.redis_unavailable")
            return None

    def _build_flow(self, redis: Any | None, scan_id: Any) -> Any:
        from src.scanning import CancelToken
        from src.scans.worker.events import ScanEventEmitter
        from src.scans.worker.flow import WorkerFlow

        emit = ScanEventEmitter(
            scan_id=scan_id, repo=self.scan_event_repository, redis=redis
        )
        cancel = CancelToken(redis, scan_id)
        return WorkerFlow(
            scan_repository=self.scan_repository,
            finding_repository=self.finding_repository,
            emit=emit,
            cancel=cancel,
            command_bus=self.command_bus,
            agentic_surface_repository=self.agentic_surface_repository,
            site_repository=self.site_repository,
            notification_prefs_repository=self.notification_prefs_repository,
            user_repository=self.user_repository,
            alert_repository=self.alert_repository,
        )

    async def _record_error(self, scan_id: Any, redis: Any | None, exc: Exception) -> None:
        from src.common.domain.enums.scans import ScanStatus

        try:
            await self.scan_repository.update_progress(
                scan_id, status=str(ScanStatus.FAILED), error=str(exc)
            )
            from src.scans.worker.events import ScanEventEmitter

            # Seed seq past any events the flow already emitted so the terminal
            # error never collides with UNIQUE (scan_id, seq).
            last_seq = 0
            if self.scan_event_repository is not None:
                try:
                    last_seq = max(await self.scan_event_repository.next_seq(scan_id) - 1, 0)
                except Exception:  # noqa: BLE001
                    last_seq = 0
            emitter = ScanEventEmitter(
                scan_id=scan_id, repo=self.scan_event_repository, redis=redis, seq=last_seq
            )
            await emitter.error(f"Escaneo falló: {type(exc).__name__}")
        except Exception:  # noqa: BLE001 - best-effort error recording
            logger.warning("run_scan.error_record_failed", scan_id=str(scan_id))

    @staticmethod
    async def _close_redis(redis: Any | None) -> None:
        if redis is not None:
            try:
                await redis.aclose()
            except Exception:  # noqa: BLE001
                pass
