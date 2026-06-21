"""``WorkerFlow`` partial-coverage status (05-agent-team plan §9).

When a BASE scanner (nuclei/testssl/security_headers) fails, the scan must close
``partial`` (NOT ``failed``), record the coverage trace, and still persist the good
findings + a coverage Finding-meta.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from expects import be_true, contain, equal, expect

from src.common.domain.enums.scans import ScanStatus
from src.scanning import ToolResult
from src.scans.worker.flow import WorkerFlow

from ._helpers import FakeFindingRepo, FakeScanRepo, RecordingEmitter, make_cancel, make_scan

_NUCLEI_LINE = json.dumps(
    {
        "template-id": "x",
        "matched-at": "https://gob.mx",
        "info": {"name": "X", "severity": "medium", "classification": {"cwe-id": ["CWE-79"]}},
    }
)


def _ok(tool: str, stdout: str = "") -> ToolResult:
    return ToolResult(tool=tool, ok=True, stdout=stdout, stderr="", duration_s=1.0, timed_out=False)


def _failed(tool: str) -> ToolResult:
    return ToolResult(
        tool=tool,
        ok=False,
        stdout="",
        stderr="waf",
        duration_s=1.0,
        timed_out=False,
        coverage_note=f"tool {tool} no completó: WAF",
    )


async def _run_tool_testssl_fails(spec, *, target, host_shared_dir, cancel, flags=()):
    tool = str(getattr(spec, "tool", ""))
    if "testssl" in tool:  # a BASE tool fails ⇒ partial
        return _failed(tool)
    if "nuclei" in tool:
        return _ok(tool, _NUCLEI_LINE)
    return _ok(tool, "")


async def test_base_tool_failure_makes_scan_partial_not_failed():
    scan_id = uuid4()
    scan_repo = FakeScanRepo(scan=make_scan(scan_id, requested_by=uuid4()))
    finding_repo = FakeFindingRepo()
    emit = RecordingEmitter()

    flow = WorkerFlow(
        scan_repository=scan_repo,
        finding_repository=finding_repo,
        emit=emit,
        cancel=make_cancel(),
    )

    with patch(
        "src.scans.worker.tools.owasp.run_tool",
        AsyncMock(side_effect=_run_tool_testssl_fails),
    ):
        scan = await flow.run(scan_id, "https://gob.mx", "basico", is_gov=True)

    expect(scan.status).to(equal(str(ScanStatus.PARTIAL)))
    # Coverage reflects the failure of the base tool.
    expect(scan.tools_status.get("testssl")).to(equal("failed"))
    # The good nuclei finding still persisted alongside the coverage meta.
    titles = [u.title for u in finding_repo.upserts]
    has_real = any(u.severity != "info" for u in finding_repo.upserts)
    has_meta = any(u.severity == "info" for u in finding_repo.upserts)
    expect(has_real).to(be_true)
    expect(has_meta).to(be_true)
    # Terminal event is done (the scan closed cleanly, just degraded).
    types = [t for _, t in emit.events]
    expect(types[-1]).to(equal("done"))
    expect(titles).to(contain("Cobertura incompleta: testssl"))
