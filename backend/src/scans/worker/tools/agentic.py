"""Agentic-surface tool — **STUB** with the seam 03-agentic-surface implements.

The base OWASP scan must run end-to-end NOW, before 03 lands. This module ships a
placeholder agentic probe that reports ``no_surface`` and contributes no findings,
so the worker, scoring and persistence all work today. Feature 03 replaces the
stub by providing a real :data:`AgenticProbe` implementation; nothing else in the
worker changes.

=========================  THE 03 SEAM (frozen contract)  =====================

``agentic_probe`` is an async callable with this EXACT signature:

    async def agentic_probe(
        target: str,
        *,
        level: str,                 # ScanLevel value: "basico"|"intermedio"|"avanzado"
        is_gov: bool,               # gov ⇒ Playwright-native CAMINO A only, never garak/promptfoo
        cancel: CancelToken,        # 04 — checked between probes
        emit: ScanEventEmitter,     # 10 — tool_start/tool_end/finding live events
        host_shared_dir: str,       # 04 — shared evidence dir for screenshots
    ) -> AgenticResult: ...

It MUST return one :class:`src.scans.domain.contracts.finding.AgenticResult` with:

    - type: "chatbot" | "prompt_input" | "search_ai"   (the detected surface kind)
    - vendor: str | None                                (Intercom/Drift/... or None)
    - location_url: str                                 (where the surface lives)
    - inferred_model: str | None                        (best-effort; None if hidden)
    - agentic_status: "no_surface" | "detected_not_tested" | "tested"
    - findings: list[Finding]   (source="agentic", category LLM01..LLM10, evidence
                                 = {payload, respuesta_cruda, veredicto, reason};
                                 confidence "alta" when a canary/regex fired, "media"
                                 for an LLM-judge verdict)

03 wires its implementation in two equivalent ways (pick one):
  (a) pass ``agentic_probe=<impl>`` to ``build_agentic_agent`` / ``build_team``
      / ``WorkerFlow`` (dependency injection — preferred, keeps imports lazy); or
  (b) replace :data:`DEFAULT_AGENTIC_PROBE` in this module.

The worker calls the probe directly (deterministic path) AND exposes it as the
``agentic_agent`` tool; either way the returned ``AgenticResult`` is what drives
``scans.agentic_status`` and the agentic sub-score (07). The agentic surface ROW
persistence (``AgenticSurfaceRepository.add``) is wired by 03 once it adds
``agentic_surface_repository`` to ``DomainContext`` (today it is not in the
context, so the worker tolerates its absence and persists no agentic row).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from src.common.application.logging import get_logger
from src.scanning import CancelToken
from src.scans.domain.contracts.finding import AgenticResult
from src.scans.worker.events import ScanEventEmitter
from src.scans.worker.tools._accumulate import accumulate_agentic

logger = get_logger(__name__)

#: The seam type 03 implements. Keyword-only context, returns one AgenticResult.
AgenticProbe = Callable[..., Awaitable[AgenticResult]]


async def stub_agentic_probe(
    target: str,
    *,
    level: str = "basico",
    is_gov: bool = False,
    cancel: CancelToken | None = None,
    emit: ScanEventEmitter | None = None,
    host_shared_dir: str = "",
) -> AgenticResult:
    """Placeholder probe: report ``no_surface``, contribute no findings.

    Replaced by 03 with the real Playwright-native attack bridge + LLM-judge +
    canary. Keeping the same signature means 03 is a drop-in. Emits a single
    ``agent_status`` so the live view shows the agentic carril ran.
    """
    if emit is not None:
        await emit.agent_status(
            "Superficie agéntica: sin chatbot/entrada de IA detectada",
            agent="Agentic Surface Auditor",
        )
    logger.info("agentic_probe.stub", extra={"target": target, "level": level})
    return AgenticResult(
        type="chatbot",
        vendor=None,
        location_url=target,
        inferred_model=None,
        agentic_status="no_surface",
        findings=[],
    )


#: Module-level default; 03 may overwrite this OR inject its own probe.
DEFAULT_AGENTIC_PROBE: AgenticProbe = stub_agentic_probe


def make_agentic_tool(
    *,
    target: str,
    host_shared_dir: str,
    cancel: CancelToken,
    emit: ScanEventEmitter,
    level: str,
    is_gov: bool,
    probe: AgenticProbe | None = None,
) -> Callable[..., Awaitable[str]]:
    """Build the closed-over agentic tool-function for the Sonnet agent.

    Runs ``probe`` (defaulting to the stub / module default), pushes its
    ``AgenticResult`` into ``session_state['agentic']`` and its findings into
    ``session_state['findings']``, and returns a short status string. 03 supplies
    the real ``probe``; the rest of the worker is unchanged.
    """
    active_probe = probe or DEFAULT_AGENTIC_PROBE

    async def run(run_context: Any | None = None) -> str:
        result = await active_probe(
            target,
            level=level,
            is_gov=is_gov,
            cancel=cancel,
            emit=emit,
            host_shared_dir=host_shared_dir,
        )
        if run_context is not None:
            accumulate_agentic(run_context, [result])
            if result.findings:
                from src.scans.worker.tools._accumulate import accumulate

                accumulate(run_context, list(result.findings))
        return (
            f"superficie agéntica: {result.agentic_status} "
            f"({len(result.findings)} hallazgos)"
        )

    run.__name__ = "run_agentic_surface"
    run.__doc__ = (
        "Detecta y prueba chatbots / entradas de IA (superficie agéntica) y "
        "mapea a OWASP-LLM Top 10."
    )
    return run
