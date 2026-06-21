"""The agentic tool accumulates into session_state, and the flow persists the
detected surface to the agentic_surface repository (spec §2.3/§7, plan §2.2/§3.4).

- The tool-function pushes its AgenticResult into ``session_state['agentic']`` and
  its findings into ``session_state['findings']``, returning a short string (not
  the data) — the LLM is never in the data path.
- ``WorkerFlow._persist_agentic`` writes one ``agentic_surface`` row per detected
  surface (skipping ``no_surface``), via the injected repo.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from expects import be_a, equal, expect, have_len

from src.scans.domain.contracts.finding import AgenticResult, Finding
from src.scans.worker.flow import WorkerFlow
from src.scans.worker.tools.agentic import make_agentic_tool


def _agentic_result(status: str, *, with_finding: bool = False) -> AgenticResult:
    findings = []
    if with_finding:
        findings = [
            Finding(
                source="agentic",
                tool="agentic-bridge",
                category="LLM01",
                title="canary leak",
                severity="high",
                confidence="alta",
                description="d",
                impact="i",
                remediation="r",
            )
        ]
    return AgenticResult(
        type="chatbot",
        vendor="Intercom",
        location_url="https://x.com",
        inferred_model=None,
        agentic_status=status,
        findings=findings,
    )


async def test_tool_pushes_result_and_findings_into_state():
    async def fake_probe(target: str, **kw: Any) -> AgenticResult:
        return _agentic_result("tested", with_finding=True)

    emit = MagicMock()
    cancel = MagicMock()
    state: dict[str, Any] = {"findings": [], "agentic": []}
    tool = make_agentic_tool(
        target="https://x.com",
        host_shared_dir="/tmp",
        cancel=cancel,
        emit=emit,
        level="intermedio",
        is_gov=False,
        probe=fake_probe,
    )
    returned = await tool(state)
    expect(returned).to(be_a(str))
    expect(state["agentic"]).to(have_len(1))
    expect(state["findings"]).to(have_len(1))
    expect("tested" in returned).to(equal(True))


def _flow_with_repo(repo: Any) -> WorkerFlow:
    return WorkerFlow(
        scan_repository=MagicMock(),
        finding_repository=MagicMock(),
        emit=MagicMock(),
        cancel=MagicMock(),
        agentic_surface_repository=repo,
    )


async def test_flow_persists_detected_surface_row():
    repo = MagicMock()
    repo.add = AsyncMock()
    flow = _flow_with_repo(repo)
    scan_id, site_id = uuid4(), uuid4()
    await flow._persist_agentic(scan_id, site_id, [_agentic_result("tested")])
    expect(repo.add.await_count).to(equal(1))
    saved = repo.add.await_args.args[0]
    expect(saved.scan_id).to(equal(scan_id))
    expect(saved.site_id).to(equal(site_id))
    expect(saved.vendor).to(equal("Intercom"))
    expect(saved.type).to(equal("chatbot"))


async def test_flow_skips_no_surface_rows():
    repo = MagicMock()
    repo.add = AsyncMock()
    flow = _flow_with_repo(repo)
    await flow._persist_agentic(uuid4(), uuid4(), [_agentic_result("no_surface")])
    expect(repo.add.await_count).to(equal(0))


async def test_flow_without_repo_is_a_noop():
    flow = WorkerFlow(
        scan_repository=MagicMock(),
        finding_repository=MagicMock(),
        emit=MagicMock(),
        cancel=MagicMock(),
        agentic_surface_repository=None,
    )
    # Must not raise even though there is no repo wired.
    await flow._persist_agentic(uuid4(), uuid4(), [_agentic_result("tested")])
