"""Shared fakes for WorkerFlow integration tests (mocked tools + repos + LLM)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from src.scans.domain.contracts.finding import Finding
from src.scans.domain.models.scan import Scan


def make_finding(
    *,
    source: str = "owasp",
    severity: str = "high",
    confidence: str = "alta",
    category: str = "A01",
    tool: str = "nuclei",
    title: str = "Finding",
    affected_url: str | None = "https://gob.mx/login",
) -> Finding:
    return Finding(
        source=source,
        tool=tool,
        category=category,
        title=title,
        severity=severity,
        confidence=confidence,
        description="d",
        affected_url=affected_url,
        impact="i",
        remediation="r",
    )


def make_scan(scan_id: UUID, *, requested_by: UUID | None = None) -> Scan:
    return Scan(
        uuid=scan_id,
        site_id=uuid4(),
        level="basico",
        status="queued",
        visibility="public",
        requested_by=requested_by,
    )


@dataclass
class FakeScanRepo:
    """Minimal in-memory ScanRepository for the flow tests."""

    scan: Scan
    progress_calls: list[dict] = field(default_factory=list)
    persisted: Scan | None = None

    async def find(self, scan_id: UUID) -> Scan | None:
        return self.scan

    async def update_progress(self, scan_id: UUID, **kw: Any) -> None:
        self.progress_calls.append(kw)

    async def persist(self, scan: Scan) -> Scan:
        self.persisted = scan
        self.scan = scan
        return scan


@dataclass
class FakeFindingRepo:
    upserts: list[Any] = field(default_factory=list)
    marked_absent: list[Any] = field(default_factory=list)

    async def upsert(self, finding: Any) -> Any:
        self.upserts.append(finding)
        return finding

    async def mark_fixed_absent(self, site_id: UUID, present_keys: list[str]) -> int:
        self.marked_absent.append((site_id, present_keys))
        return 0


@dataclass
class RecordingEmitter:
    """A ScanEventEmitter-compatible recorder (no PG/Redis)."""

    events: list[tuple[int, str]] = field(default_factory=list)
    _seq: int = 0

    def __post_init__(self) -> None:
        self.scan_id = uuid4()

    async def _emit(self, type_: str) -> None:
        self._seq += 1
        self.events.append((self._seq, type_))

    async def agent_status(self, *a: Any, **k: Any) -> None:
        await self._emit("agent_status")

    async def tool_start(self, *a: Any, **k: Any) -> None:
        await self._emit("tool_start")

    async def tool_end(self, *a: Any, **k: Any) -> None:
        await self._emit("tool_end")

    async def finding(self, *a: Any, **k: Any) -> None:
        await self._emit("finding")

    async def phase(self, *a: Any, **k: Any) -> None:
        await self._emit("phase")

    async def score(self, *a: Any, **k: Any) -> None:
        await self._emit("score")

    async def done(self, *a: Any, **k: Any) -> None:
        await self._emit("done")

    async def error(self, *a: Any, **k: Any) -> None:
        await self._emit("error")


def make_cancel(set_: bool = False) -> MagicMock:
    cancel = MagicMock()
    cancel.is_set = AsyncMock(return_value=set_)
    return cancel
