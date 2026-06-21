"""``RunScanCommand`` — the SAQ background job that runs a pentest (12-api → 05).

``EnqueueScan`` (12) dispatches this command with ``run_async=True`` so the
``SaqCommandEnqueuer`` hands it to the SAQ queue; the agent team (05-agent-team)
registers the handler that actually orchestrates Opus + Sonnet + the scanners.
12-api only owns the command *shape* (``scan_id``) and the enqueue call — never
the execution. Keeping the command in ``scans`` avoids a layer cycle while the
worker plugs in its handler later.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

from src.common.domain.buses.commands import Command


@dataclass
class RunScanCommand(Command):
    scan_id: UUID

    @property
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scan_id"] = str(self.scan_id)
        return data

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> RunScanCommand:
        scan_id = kwargs["scan_id"]
        return cls(scan_id=scan_id if isinstance(scan_id, UUID) else UUID(str(scan_id)))
