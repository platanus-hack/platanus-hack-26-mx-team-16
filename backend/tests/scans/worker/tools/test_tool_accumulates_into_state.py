"""The tool pushes Finding[] into session_state and returns a short string
(05-agent-team plan §9): findings NEVER travel through the return value (LLM).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from expects import be_a, equal, expect, have_len

from src.scanning import ToolResult
from src.scans.domain.contracts.finding import Finding
from src.scans.domain.enums.tool_id import ToolId
from src.scans.worker.tools._accumulate import accumulate, accumulate_agentic
from src.scans.worker.tools.owasp import make_owasp_tool


def _factory_finding() -> Finding:
    return Finding(
        source="owasp",
        tool="nuclei",
        category="A01",
        title="t",
        severity="high",
        confidence="alta",
        description="d",
        impact="i",
        remediation="r",
    )


def test_accumulate_appends_to_session_state_dict():
    state: dict = {}
    accumulate(state, [_factory_finding()])
    accumulate(state, [_factory_finding()])
    expect(state["findings"]).to(have_len(2))


def test_accumulate_reads_run_context_session_state_attribute():
    class FakeRunContext:
        def __init__(self):
            self.session_state = {"findings": []}

    ctx = FakeRunContext()
    accumulate(ctx, [_factory_finding()])
    expect(ctx.session_state["findings"]).to(have_len(1))


def test_accumulate_agentic_uses_separate_bucket():
    state: dict = {}
    accumulate_agentic(state, ["fake-agentic-result"])
    expect(state["agentic"]).to(equal(["fake-agentic-result"]))


async def test_tool_returns_short_string_not_findings():
    state: dict = {"findings": []}
    line = json.dumps(
        {"template-id": "x", "matched-at": "u", "info": {"name": "X", "severity": "low"}}
    )
    ok = ToolResult(tool="nuclei", ok=True, stdout=line, stderr="", duration_s=1.0, timed_out=False)
    emit = MagicMock()
    emit.tool_start = AsyncMock()
    emit.tool_end = AsyncMock()
    cancel = MagicMock()
    cancel.is_set = AsyncMock(return_value=False)

    with patch("src.scans.worker.tools.owasp.run_tool", AsyncMock(return_value=ok)):
        tool = make_owasp_tool(
            ToolId.NUCLEI,
            target="u",
            host_shared_dir="/tmp",
            cancel=cancel,
            emit=emit,
        )
        returned = await tool(state)

    # The findings are in state, the return is a short status string.
    expect(returned).to(be_a(str))
    expect(state["findings"]).to(have_len(1))
    expect("nuclei" in returned).to(equal(True))
