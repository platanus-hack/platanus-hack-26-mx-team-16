"""``WorkerFlow`` cancellation + budget exhaustion (05-agent-team plan §9).

Cancel (Redis flag) ⇒ no further tool starts, scan closes ``cancelled``, the
accumulated state persists, the run does not hang. Budget exhaustion
(``ScanBudgetExceeded`` from the watchdog) ⇒ same terminal contract.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from expects import equal, expect

from src.common.domain.enums.scans import ScanStatus
from src.scanning import ScanBudgetExceeded, ToolResult
from src.scans.worker.flow import WorkerFlow

from ._helpers import FakeFindingRepo, FakeScanRepo, RecordingEmitter, make_cancel, make_scan


def _ok(tool: str) -> ToolResult:
    return ToolResult(tool=tool, ok=True, stdout="", stderr="", duration_s=1.0, timed_out=False)


async def _run_tool(spec, *, target, host_shared_dir, cancel, flags=()):
    return _ok(str(getattr(spec, "tool", "")))


async def test_cancel_flag_set_closes_cancelled_without_running_tools():
    scan_id = uuid4()
    scan_repo = FakeScanRepo(scan=make_scan(scan_id, requested_by=uuid4()))
    finding_repo = FakeFindingRepo()
    emit = RecordingEmitter()

    flow = WorkerFlow(
        scan_repository=scan_repo,
        finding_repository=finding_repo,
        emit=emit,
        cancel=make_cancel(set_=True),  # cancel flag already raised
    )

    run_tool_mock = AsyncMock(side_effect=_run_tool)
    with patch("src.scans.worker.tools.owasp.run_tool", run_tool_mock):
        scan = await flow.run(scan_id, "https://gob.mx", "basico", is_gov=True)

    expect(scan.status).to(equal(str(ScanStatus.CANCELLED)))
    # No OWASP tool was launched (cancel checked before the first tool).
    expect(run_tool_mock.await_count).to(equal(0))
    # The stream still closed: terminal done with cancelled outcome.
    types = [t for _, t in emit.events]
    expect(types[-1]).to(equal("done"))


async def test_budget_exceeded_closes_cancelled_and_persists_partial_state():
    scan_id = uuid4()
    scan_repo = FakeScanRepo(scan=make_scan(scan_id, requested_by=uuid4()))
    finding_repo = FakeFindingRepo()
    emit = RecordingEmitter()

    flow = WorkerFlow(
        scan_repository=scan_repo,
        finding_repository=finding_repo,
        emit=emit,
        cancel=make_cancel(),  # not cancelled; the watchdog fires instead
    )

    async def blow_budget(_coro):
        # Close the coroutine we were handed (mirror the real wait_for) then raise.
        if hasattr(_coro, "close"):
            _coro.close()
        raise ScanBudgetExceeded("budget")

    with patch("src.scans.worker.flow.run_with_watchdog", side_effect=blow_budget):
        scan = await flow.run(scan_id, "https://gob.mx", "basico", is_gov=True)

    expect(scan.status).to(equal(str(ScanStatus.CANCELLED)))
    # Still finalized + persisted (no hang); terminal done emitted last.
    expect(scan_repo.persisted).not_to(equal(None))
    types = [t for _, t in emit.events]
    expect(types[-1]).to(equal("done"))
