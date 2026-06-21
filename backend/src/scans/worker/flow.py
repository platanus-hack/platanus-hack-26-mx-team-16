"""``WorkerFlow`` — the per-scan choreographer (spec §5, plan §4).

This is the integration hub that glues 04 (tools) + 06 (data/repos) + 07
(scoring) + 10 (events) + 08 (alerts) together. It does NOT parse, score, or
narrate itself — it sequences the deterministic pieces and persists:

    running → resolve_tools (04) → run each tool wrapper (parse → Finding[] into
    session_state) under the global-budget watchdog + CancelToken → dedupe +
    compute_score (07) → persist findings (UPSERT) + scan scores → emit typed
    events throughout (10) → synthesize executive summary (Opus, the only LLM in
    the report path) → terminal done. On partial failure: coverage Finding-meta +
    status=partial. For CRON-origin scans (requested_by IS NULL): EvaluateSiteAlerts (08).

The LLM-driven Agno Team is the *orchestration veneer*; the data path is
LLM-free. ``run`` executes the closed-over tool wrappers directly (the
deterministic, demo-critical path) and OPTIONALLY drives the Team for live
coordination when ``run_team`` is provided. This keeps the whole findings →
dedupe → score → persist → emit pipeline unit-testable without agno/anthropic.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.common.application.logging import get_logger
from src.common.domain.buses.commands import CommandBus
from src.common.domain.enums.scans import (
    AgenticStatus,
    FindingStatus,
    ScanStatus,
)
from src.common.settings import settings
from src.scanning import (
    CancelToken,
    ScanBudgetExceeded,
    resolve_tools,
    run_with_watchdog,
)
from src.scanning.evidence import ensure_scan_dir
from src.scans.domain.contracts.finding import AgenticResult, Finding
from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.models.scan import Scan
from src.scans.domain.repositories.agentic_surface import AgenticSurfaceRepository
from src.scans.domain.repositories.finding import FindingRepository
from src.scans.domain.repositories.scan import ScanRepository
from src.scans.domain.services.dedupe import compute_dedupe_key
from src.scans.domain.services.scoring import ScoreInput, compute_score, dedupe
from src.scans.worker.events import ScanEventEmitter
from src.scans.worker.summary import synthesize_summary
from src.scans.worker.tools.agentic import AgenticProbe
from src.scans.worker.tools.owasp import build_owasp_tools

logger = get_logger(__name__)

#: Tools whose absence flips the scan to ``partial`` (the base battery, spec §5.5).
BASE_TOOLS: frozenset[str] = frozenset(
    {"nuclei", "testssl", "security_headers"}
)

#: Signature of an async tool wrapper (the closures from ``build_owasp_tools``).
ToolFn = Callable[..., Awaitable[str]]


@dataclass
class WorkerFlow:
    """Choreographs one scan end-to-end. Construct with the per-scan deps.

    Repos come from ``DomainContext`` (06); ``emit`` is 10's ``ScanEventEmitter``;
    ``cancel`` is 04's ``CancelToken``. ``agentic_surface_repository`` is optional;
    03 added it to ``DomainContext`` so production persists the agentic row, but it
    stays optional so tests can omit it (when absent, agentic rows are simply not
    persisted). ``command_bus`` is needed only for the CRON alert evaluation (08).
    """

    scan_repository: ScanRepository
    finding_repository: FindingRepository
    emit: ScanEventEmitter
    cancel: CancelToken
    command_bus: CommandBus | None = None
    agentic_surface_repository: AgenticSurfaceRepository | None = None
    agentic_probe: AgenticProbe | None = None
    #: Extra repos for the CRON alert path (08). Optional: only the SAQ handler
    #: wiring supplies them; tests omit them. All-or-nothing — if any is None the
    #: alert evaluation is skipped.
    site_repository: Any | None = None
    notification_prefs_repository: Any | None = None
    user_repository: Any | None = None
    alert_repository: Any | None = None
    #: Optional Agno Team runner (LLM coordination). Receives (session_state) and
    #: drives the members; when None, the flow runs the tool wrappers directly.
    run_team: Callable[[dict[str, Any]], Awaitable[None]] | None = None

    async def run(self, scan_id: UUID, url: str, level: str, is_gov: bool) -> Scan:
        """Execute the full scan flow for ``scan_id``. Never raises on tool failure.

        Returns the persisted terminal ``Scan``. A hard failure outside the tools
        (DB/assembly) is re-raised; the SAQ ``run_scan_handler`` catches it and
        records ``status=failed`` (a terminal error event), so the live view
        always closes.
        """
        await self._mark_running(scan_id)

        session_state: dict[str, Any] = {"findings": [], "agentic": []}
        coverage: dict[str, str] = {}
        invocations = self._resolve(is_gov, level)
        ensure_scan_dir(scan_id)

        outcome = "success"
        budget_exceeded = False
        try:
            await self._execute(
                scan_id,
                url=url,
                level=level,
                is_gov=is_gov,
                invocations=invocations,
                session_state=session_state,
                coverage=coverage,
            )
        except ScanBudgetExceeded:
            budget_exceeded = True
            outcome = "cancelled"
            logger.warning("worker_flow.budget_exceeded", extra={"scan_id": str(scan_id)})

        cancelled = budget_exceeded or await self.cancel.is_set()

        scan = await self._finalize(
            scan_id,
            url=url,
            is_gov=is_gov,
            session_state=session_state,
            coverage=coverage,
            invocations=invocations,
            cancelled=cancelled,
        )

        await self._maybe_evaluate_alerts(scan)

        done_outcome = "cancelled" if cancelled else outcome
        await self.emit.done("Escaneo finalizado", outcome=done_outcome)
        return scan

    # -- phases ----------------------------------------------------------------

    async def _mark_running(self, scan_id: UUID) -> None:
        await self.scan_repository.update_progress(
            scan_id, status=str(ScanStatus.RUNNING), progress=0, current_phase="iniciando"
        )
        await self.emit.agent_status("Iniciando escaneo", agent="worker")

    def _resolve(self, is_gov: bool, level: str):
        from src.common.domain.enums.scans import ScanLevel

        scan_level = ScanLevel(level) if not isinstance(level, ScanLevel) else level
        return resolve_tools(is_gov=is_gov, level=scan_level)

    async def _execute(
        self,
        scan_id: UUID,
        *,
        url: str,
        level: str,
        is_gov: bool,
        invocations: list[Any],
        session_state: dict[str, Any],
        coverage: dict[str, str],
    ) -> None:
        """Run the tool battery under the global watchdog (spec §5.3).

        Prefers the injected Agno Team runner (LLM coordination); otherwise runs
        the closed-over OWASP tool wrappers directly. Either way the findings land
        in ``session_state`` via ``accumulate`` — the LLM is never in the data path.
        """
        async def scan_coro() -> None:
            if self.run_team is not None:
                # The Team's ``agentic_agent`` already owns the agentic tool, so
                # the Team path runs the probe itself. Calling ``_run_agentic``
                # here too would run the probe TWICE for one scan — guard it to
                # the direct (non-Team) path only.
                await self.run_team(session_state)
            else:
                await self._run_tools_directly(
                    url=url,
                    level=level,
                    is_gov=is_gov,
                    invocations=invocations,
                    session_state=session_state,
                    coverage=coverage,
                )
                await self._run_agentic(
                    url=url, level=level, is_gov=is_gov, session_state=session_state
                )

        await run_with_watchdog(scan_coro())

    async def _run_tools_directly(
        self,
        *,
        url: str,
        level: str,
        is_gov: bool,
        invocations: list[Any],
        session_state: dict[str, Any],
        coverage: dict[str, str],
    ) -> None:
        """Deterministic, LLM-free execution of the OWASP tool wrappers (spec §2)."""
        host_shared_dir = str(ensure_scan_dir(self.emit.scan_id))
        tools: list[ToolFn] = build_owasp_tools(
            invocations,
            target=url,
            host_shared_dir=host_shared_dir,
            cancel=self.cancel,
            emit=self.emit,
            coverage=coverage,
        )
        total = max(len(tools), 1)
        for i, tool in enumerate(tools, start=1):
            if await self.cancel.is_set():
                logger.info("worker_flow.cancelled_between_tools")
                break
            await tool(session_state)
            progress = int(80 * i / total)
            await self.emit.phase("Ejecutando herramientas", progress=progress)

    async def _run_agentic(
        self,
        *,
        url: str,
        level: str,
        is_gov: bool,
        session_state: dict[str, Any],
    ) -> None:
        """Run the agentic probe (the real 03 probe by default; an injected
        ``agentic_probe`` fake overrides it for tests)."""
        from src.scans.worker.tools.agentic import make_agentic_tool

        host_shared_dir = str(ensure_scan_dir(self.emit.scan_id))
        tool = make_agentic_tool(
            target=url,
            host_shared_dir=host_shared_dir,
            cancel=self.cancel,
            emit=self.emit,
            level=level,
            is_gov=is_gov,
            probe=self.agentic_probe,
        )
        await tool(session_state)

    async def _finalize(
        self,
        scan_id: UUID,
        *,
        url: str,
        is_gov: bool,
        session_state: dict[str, Any],
        coverage: dict[str, str],
        invocations: list[Any],
        cancelled: bool,
    ) -> Scan:
        """Dedupe + score (07) + persist findings/scores + summary (spec §5.4/§5.5)."""
        raw_findings: list[Finding] = list(session_state.get("findings", []))
        agentic_results: list[AgenticResult] = list(session_state.get("agentic", []))

        deduped = dedupe(raw_findings)
        agentic_status = self._agentic_status(agentic_results)
        partial = self._is_partial(coverage, invocations)

        score = compute_score(
            ScoreInput(
                findings=deduped,
                agentic_status=agentic_status,
                partial_coverage=partial,
            )
        )

        scan = await self.scan_repository.find(scan_id)
        if scan is None:
            raise RuntimeError(f"scan {scan_id} disappeared mid-flow")

        site_id = scan.site_id
        await self._persist_findings(scan_id, site_id, deduped)
        await self._persist_agentic(scan_id, site_id, agentic_results)

        summary = await synthesize_summary(deduped, score)

        status = self._terminal_status(cancelled=cancelled, partial=partial)
        coverage_rows = self._coverage_rows(coverage)

        scan = scan.model_copy(
            update={
                "status": status,
                "web_score": score.web_score,
                "agentic_score": score.agentic_score,
                "overall_score": score.overall_score,
                "overall_grade": score.overall_grade,
                "agentic_status": agentic_status.value,
                "penalty_raw": score.penalty_raw,
                "summary": summary.model_dump(),
                "coverage": coverage_rows,
                "tools_status": dict(coverage),
                "progress": 100,
                "current_phase": "finalizado",
                "finished_at": datetime.now(UTC),
            }
        )
        scan = await self.scan_repository.persist(scan)

        await self.emit.score(
            f"Calificación {score.overall_grade}",
            payload={
                "overall_grade": score.overall_grade,
                "overall_score": score.overall_score,
                "web_score": score.web_score,
                "agentic_score": score.agentic_score,
            },
            progress=100,
        )
        return scan

    async def _persist_findings(
        self, scan_id: UUID, site_id: UUID, findings: list[Finding]
    ) -> None:
        for f in findings:
            record = self._to_record(scan_id, site_id, f)
            await self.finding_repository.upsert(record)
            await self.emit.finding(f.title, severity=f.severity)
        # A finding that stops reappearing at the site level is resolved (06 §3.3).
        present_keys = [
            compute_dedupe_key(
                site_id=str(site_id),
                source=f.source,
                category=f.category,
                affected_url=f.affected_url,
                param=f.param,
                tool=f.tool,
            )
            for f in findings
        ]
        await self.finding_repository.mark_fixed_absent(site_id, present_keys)

    async def _persist_agentic(
        self, scan_id: UUID, site_id: UUID, results: list[AgenticResult]
    ) -> None:
        if self.agentic_surface_repository is None:
            return  # 03 wires the repo into DomainContext; until then, skip rows.
        from src.scans.domain.models.agentic_surface import AgenticSurface

        for result in results:
            if result.agentic_status == AgenticStatus.NO_SURFACE.value:
                continue
            await self.agentic_surface_repository.add(
                AgenticSurface(
                    uuid=uuid4(),
                    scan_id=scan_id,
                    site_id=site_id,
                    type=result.type,
                    vendor=result.vendor,
                    location_url=result.location_url,
                    inferred_model=result.inferred_model,
                )
            )

    async def _maybe_evaluate_alerts(self, scan: Scan) -> None:
        """CRON-origin scans (requested_by IS NULL) evaluate site alerts (08).

        The use case self-gates on ``requested_by`` too, but we also require the
        alert repos to have been wired (only the SAQ handler supplies them).
        """
        if scan.requested_by is not None or self.command_bus is None:
            return
        alert_repos = (
            self.site_repository,
            self.notification_prefs_repository,
            self.user_repository,
            self.alert_repository,
        )
        if any(r is None for r in alert_repos):
            return
        from src.scans.application.use_cases.evaluate_site_alerts import (
            EvaluateSiteAlerts,
        )

        try:
            await EvaluateSiteAlerts(
                scan_id=scan.uuid,
                scan_repository=self.scan_repository,
                finding_repository=self.finding_repository,
                site_repository=self.site_repository,
                notification_prefs_repository=self.notification_prefs_repository,
                user_repository=self.user_repository,
                alert_repository=self.alert_repository,
                command_bus=self.command_bus,
            ).execute()
        except Exception:  # noqa: BLE001 - alerts must never fail the scan
            logger.warning("worker_flow.alert_eval_failed", extra={"scan_id": str(scan.uuid)})

    # -- helpers ---------------------------------------------------------------

    def _to_record(self, scan_id: UUID, site_id: UUID, f: Finding) -> FindingRecord:
        dedupe_key = compute_dedupe_key(
            site_id=str(site_id),
            source=f.source,
            category=f.category,
            affected_url=f.affected_url,
            param=f.param,
            tool=f.tool,
        )
        return FindingRecord(
            uuid=uuid4(),
            scan_id=scan_id,
            site_id=site_id,
            source=f.source,
            tool=f.tool,
            category=f.category,
            title=f.title,
            severity=f.severity,
            cvss=f.cvss,
            confidence=f.confidence,
            description=f.description,
            evidence=f.evidence,
            affected_url=f.affected_url,
            endpoint=f.endpoint,
            param=f.param,
            impact=f.impact,
            remediation=f.remediation,
            references=f.references,
            status=str(FindingStatus.OPEN),
            dedupe_key=dedupe_key,
        )

    @staticmethod
    def _agentic_status(results: list[AgenticResult]) -> AgenticStatus:
        """Resolve the scan-level agentic status from the probe results.

        ``tested`` wins over ``detected_not_tested`` over ``no_surface``; an empty
        result list means ``no_surface``.
        """
        statuses = {r.agentic_status for r in results}
        if AgenticStatus.TESTED.value in statuses:
            return AgenticStatus.TESTED
        if AgenticStatus.DETECTED_NOT_TESTED.value in statuses:
            return AgenticStatus.DETECTED_NOT_TESTED
        return AgenticStatus.NO_SURFACE

    @staticmethod
    def _is_partial(coverage: dict[str, str], invocations: list[Any]) -> bool:
        """Partial when any resolved BASE tool did not complete cleanly (spec §5.5)."""
        resolved = {str(getattr(inv, "tool", inv)) for inv in invocations}
        base_resolved = resolved & BASE_TOOLS
        for tool in base_resolved:
            if coverage.get(tool, "ok") != "ok":
                return True
        # Also partial if a base tool was resolved but never recorded coverage.
        return any(tool not in coverage for tool in base_resolved)

    @staticmethod
    def _terminal_status(*, cancelled: bool, partial: bool) -> str:
        if cancelled:
            return str(ScanStatus.CANCELLED)
        if partial:
            return str(ScanStatus.PARTIAL)
        return str(ScanStatus.DONE)

    @staticmethod
    def _coverage_rows(coverage: dict[str, str]) -> list[dict[str, Any]]:
        return [{"tool": tool, "status": status} for tool, status in coverage.items()]
