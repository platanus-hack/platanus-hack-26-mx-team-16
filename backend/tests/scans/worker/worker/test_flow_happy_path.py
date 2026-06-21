"""``WorkerFlow.run`` happy path (05-agent-team plan §9).

The Agno Team is NOT driven here (``run_team=None`` ⇒ deterministic tool wrappers).
``run_tool`` (04) is mocked so the OWASP battery yields findings without launching
real scanners; the agentic carril is the stub (``no_surface``). The flow must:
dedupe + score (07), UPSERT findings, persist the terminal ``Scan`` with scores,
emit events with a monotonic ``seq`` and close ``done``.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from expects import be_above, contain, equal, expect, have_len

from src.common.domain.enums.scans import ScanStatus
from src.scanning import ToolResult
from src.scans.worker.flow import WorkerFlow

from ._helpers import (
    FakeFindingRepo,
    FakeScanRepo,
    RecordingEmitter,
    make_cancel,
    make_scan,
)

_NUCLEI_LINE = json.dumps(
    {
        "template-id": "sqli-detect",
        "matched-at": "https://gob.mx/login",
        "info": {
            "name": "SQL Injection",
            "severity": "high",
            "classification": {"cwe-id": ["CWE-89"], "cvss-score": 8.6},
        },
    }
)


def _ok(tool: str, stdout: str = "") -> ToolResult:
    return ToolResult(
        tool=tool, ok=True, stdout=stdout, stderr="", duration_s=1.0, timed_out=False
    )


async def _fake_run_tool(spec, *, target, host_shared_dir, cancel, flags=()):
    tool = str(getattr(spec, "tool", getattr(spec, "id", "")))
    if "nuclei" in tool:
        return _ok(tool, _NUCLEI_LINE)
    return _ok(tool, "")


async def test_happy_path_dedupes_scores_persists_and_emits_done():
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

    with patch("src.scans.worker.tools.owasp.run_tool", AsyncMock(side_effect=_fake_run_tool)):
        scan = await flow.run(scan_id, "https://gob.mx", "basico", is_gov=True)

    # Terminal status: every base tool ran ⇒ done (not partial).
    expect(scan.status).to(equal(str(ScanStatus.DONE)))
    expect(scan.overall_grade).to(be_above(""))
    expect(scan.progress).to(equal(100))

    # The nuclei finding was persisted (UPSERT) with a dedupe_key.
    expect(len(finding_repo.upserts)).to(be_above(0))
    expect(finding_repo.upserts[0].dedupe_key).to(be_above(""))
    # mark_fixed_absent was called once with the present keys (resolution sweep).
    expect(finding_repo.marked_absent).to(have_len(1))

    # Event order: agent_status first, terminal done last, seq strictly monotonic.
    types = [t for _, t in emit.events]
    seqs = [s for s, _ in emit.events]
    expect(types[0]).to(equal("agent_status"))
    expect(types[-1]).to(equal("done"))
    expect(seqs).to(equal(sorted(seqs)))
    expect(len(set(seqs))).to(equal(len(seqs)))  # no duplicate seq
    expect(types).to(contain("score"))
    expect(types).to(contain("finding"))


async def test_team_runner_path_reads_session_state_not_llm_content():
    """When a Team runner is injected it populates ``session_state`` (LLM out of data path)."""
    scan_id = uuid4()
    scan_repo = FakeScanRepo(scan=make_scan(scan_id, requested_by=uuid4()))
    finding_repo = FakeFindingRepo()
    emit = RecordingEmitter()

    from ._helpers import make_finding

    seeded = make_finding(title="From team session_state")

    async def fake_run_team(session_state: dict) -> None:
        session_state["findings"].append(seeded)

    flow = WorkerFlow(
        scan_repository=scan_repo,
        finding_repository=finding_repo,
        emit=emit,
        cancel=make_cancel(),
        run_team=fake_run_team,
    )

    scan = await flow.run(scan_id, "https://gob.mx", "basico", is_gov=True)

    # The finding the (fake) Team wrote into session_state reached persistence —
    # the LLM is never in the data path; the worker reads the shared dict.
    titles = [u.title for u in finding_repo.upserts]
    expect(titles).to(contain("From team session_state"))
    # A Team runner owns its own coverage; with the fake not recording it, the base
    # battery is unaccounted-for ⇒ the flow degrades to partial (never failed).
    expect(scan.status).to(equal(str(ScanStatus.PARTIAL)))
