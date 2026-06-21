"""``SeedGovCommand`` / ``SeedGovHandler`` — the gov-ranking seed job
(08-ranking-watchlists §2.3, §2.4).

Reads ``fixtures/gob_mx.txt`` (~30–50 ``.gob.mx`` hostnames), inserts each as a
``sites(is_gov=true)`` row (``is_gov`` is derived server-side by
``SiteRepository.get_or_create`` — never trusted from the file), and enqueues a
**basic/passive** scan for each through the same idempotent enqueue as
``POST /scans``. Levels are hard-guarded to ``ScanLevel.BASICO``
(``AutomaticActiveScanError`` otherwise, 01-legal §3.2).

Pre-baked leaderboard fixtures (loaded via the fixtures CLI) populate the board
from second 0; these real scans only **overwrite** seeded rows if they finish in
time (§2.4) — so this job is never the critical path for the demo.
"""

from __future__ import annotations

import pathlib
from dataclasses import asdict, dataclass
from typing import Any

from src.common.application.logging import get_logger
from src.common.domain.buses.commands import Command, CommandBus, CommandHandler
from src.common.domain.enums.scans import ScanLevel, ScanVisibility
from src.scans.application.commands.enqueue_monitor_scan import enqueue_automatic_scan
from src.scans.domain.repositories.scan import ScanRepository
from src.sites.domain.repositories.site import SiteRepository

logger = get_logger(__name__)

# fixtures/gob_mx.txt relative to the backend root (where command.py / worker run).
_DEFAULT_SEED_PATH = "fixtures/gob_mx.txt"


def read_gov_seed(path: str = _DEFAULT_SEED_PATH) -> list[str]:
    """Parse the seed file: one hostname per line, ignoring blanks and ``#``."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    hosts: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        hosts.append(line)
    return hosts


@dataclass
class SeedGovCommand(Command):
    seed_path: str = _DEFAULT_SEED_PATH

    @property
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> "SeedGovCommand":
        return cls(**kwargs)


@dataclass
class SeedGovHandler(CommandHandler[SeedGovCommand]):
    site_repository: SiteRepository
    scan_repository: ScanRepository
    command_bus: CommandBus

    async def execute(self, command: SeedGovCommand) -> None:
        hosts = read_gov_seed(command.seed_path)
        inserted = 0
        enqueued = 0
        for host in hosts:
            url = host if host.startswith("http") else f"https://{host}"
            site = await self.site_repository.get_or_create(url, owner_user_id=None)
            inserted += 1
            _, created = await enqueue_automatic_scan(
                site_id=site.uuid,
                level=ScanLevel.BASICO,
                visibility=ScanVisibility.PUBLIC,
                scan_repository=self.scan_repository,
                command_bus=self.command_bus,
                is_gov=site.is_gov,
            )
            if created:
                enqueued += 1
        logger.info("seed_gov.completed", sites=inserted, scans_enqueued=enqueued)
