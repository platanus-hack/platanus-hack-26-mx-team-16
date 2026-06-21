"""OWASP tool wrapper partial-failure policy (05-agent-team plan §9).

``run_tool`` is mocked: a failed/timed-out result must degrade to a coverage
Finding-meta (severity=info, confidence=baja), record coverage, NOT raise, and let
the flow continue.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from expects import equal, expect, have_len

from src.scanning import ToolResult
from src.scans.domain.enums.tool_id import ToolId
from src.scans.worker.tools.owasp import make_owasp_tool


def _emit() -> MagicMock:
    emit = MagicMock()
    emit.tool_start = AsyncMock()
    emit.tool_end = AsyncMock()
    return emit


def _cancel(set_: bool = False) -> MagicMock:
    cancel = MagicMock()
    cancel.is_set = AsyncMock(return_value=set_)
    return cancel


async def test_failed_tool_produces_coverage_meta_and_marks_coverage():
    coverage: dict[str, str] = {}
    state: dict = {"findings": []}
    failed = ToolResult(
        tool="nuclei",
        ok=False,
        stdout="",
        stderr="boom",
        duration_s=1.0,
        timed_out=False,
        coverage_note="tool nuclei no completó: WAF",
    )

    with patch("src.scans.worker.tools.owasp.run_tool", AsyncMock(return_value=failed)):
        tool = make_owasp_tool(
            ToolId.NUCLEI,
            target="https://gob.mx",
            host_shared_dir="/tmp",
            cancel=_cancel(),
            emit=_emit(),
            coverage=coverage,
        )
        result_str = await tool(state)

    expect(state["findings"]).to(have_len(1))
    meta = state["findings"][0]
    expect(meta.severity).to(equal("info"))
    expect(meta.confidence).to(equal("baja"))
    expect(coverage["nuclei"]).to(equal("failed"))
    expect("nuclei" in result_str).to(equal(True))


async def test_timeout_marks_coverage_timeout():
    coverage: dict[str, str] = {}
    state: dict = {"findings": []}
    timed = ToolResult(
        tool="testssl",
        ok=False,
        stdout="",
        stderr="",
        duration_s=60.0,
        timed_out=True,
        coverage_note="tool testssl no completó: timeout tras 60s",
    )

    with patch("src.scans.worker.tools.owasp.run_tool", AsyncMock(return_value=timed)):
        tool = make_owasp_tool(
            ToolId.TESTSSL,
            target="https://gob.mx",
            host_shared_dir="/tmp",
            cancel=_cancel(),
            emit=_emit(),
            coverage=coverage,
        )
        await tool(state)

    expect(coverage["testssl"]).to(equal("timeout"))
    expect(state["findings"][0].severity).to(equal("info"))


async def test_successful_tool_parses_findings_and_marks_ok():
    import json

    coverage: dict[str, str] = {}
    state: dict = {"findings": []}
    line = json.dumps(
        {
            "template-id": "x",
            "matched-at": "https://gob.mx",
            "info": {"name": "X", "severity": "high", "classification": {"cwe-id": ["CWE-89"]}},
        }
    )
    ok = ToolResult(
        tool="nuclei", ok=True, stdout=line, stderr="", duration_s=2.0, timed_out=False
    )

    with patch("src.scans.worker.tools.owasp.run_tool", AsyncMock(return_value=ok)):
        tool = make_owasp_tool(
            ToolId.NUCLEI,
            target="https://gob.mx",
            host_shared_dir="/tmp",
            cancel=_cancel(),
            emit=_emit(),
            coverage=coverage,
        )
        await tool(state)

    expect(coverage["nuclei"]).to(equal("ok"))
    expect(state["findings"]).to(have_len(1))
    expect(state["findings"][0].severity).to(equal("high"))


async def test_cancelled_before_start_still_returns_meta_not_raises():
    # run_tool itself returns ok=False when cancelled before start (04 contract).
    coverage: dict[str, str] = {}
    state: dict = {"findings": []}
    cancelled = ToolResult(
        tool="nuclei",
        ok=False,
        stdout="",
        stderr="",
        duration_s=0.0,
        timed_out=False,
        coverage_note="tool nuclei no se ejecutó: scan cancelado",
    )
    with patch("src.scans.worker.tools.owasp.run_tool", AsyncMock(return_value=cancelled)):
        tool = make_owasp_tool(
            ToolId.NUCLEI,
            target="https://gob.mx",
            host_shared_dir="/tmp",
            cancel=_cancel(set_=True),
            emit=_emit(),
            coverage=coverage,
        )
        await tool(state)

    expect(state["findings"][0].severity).to(equal("info"))
    expect(coverage["nuclei"]).to(equal("failed"))
