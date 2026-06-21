"""``agentic_probe`` — the real 03 implementation that fills the 05 seam.

Orchestrates the whole agentic carril deterministically (the LLM never writes a
calculated column, plan §6.1):

    detect (2-pass) → decide whether to probe (level + legal gate) → for each
    surface, for each capped payload: bridge.send_and_read → judge → Finding →
    assemble ONE AgenticResult with agentic_status ∈ {no_surface,
    detected_not_tested, tested}.

Signature matches the frozen 05 seam EXACTLY (see
``src/scans/worker/tools/agentic.py``):

    async def agentic_probe(target, *, level, is_gov, cancel, emit,
                            host_shared_dir) -> AgenticResult

LEGAL GATE (spec §3, §4.3): active probing NEVER runs on a ``.gob.mx`` automatic /
passive scan. The gate is **passed in** (05 wiring decides whether to hand the
probe tool to the subagent; 02 attestation covers user-initiated active gov
scans). This module honors it defensively: when ``is_gov`` and the scan is on the
passive path, it detects but does not probe → ``detected_not_tested``. garak /
promptfoo are never used here (CAMINO A only).

``playwright`` and the LLM client stay lazy (imported inside the bridge / judge);
this module imports cleanly on CI. Tests inject a fake ``bridge_factory`` and
``judge_model`` and never launch a browser or call the API.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from src.common.application.logging import get_logger
from src.common.domain.enums.scans import AgenticStatus, ScanLevel
from src.common.settings import settings
from src.scans.domain.contracts.finding import AgenticResult, Finding
from src.scans.worker.agentic.bridge import PlaywrightBridge
from src.scans.worker.agentic.detector import AgenticSurface, detect_surface
from src.scans.worker.agentic.inferred_model import infer_model
from src.scans.worker.agentic.judge import judge_response, verdict_to_finding
from src.scans.worker.agentic.payloads import (
    inject_canary,
    load_payloads,
    new_canary_token,
)

logger = get_logger(__name__)

AGENTIC_AGENT_NAME = "Agentic Surface Auditor"

#: Demo hosts the bridge may reach despite the loopback egress guard (the planted
#: bot). Read from settings; ``localhost`` is always permitted for the demo bot.
_DEFAULT_DEMO_HOSTS = frozenset({"localhost", "127.0.0.1", "planted-bot"})

#: A factory returning a ``PlaywrightBridge``-like async context manager. Injected
#: in tests so no real browser launches.
BridgeFactory = Callable[..., Any]


def decide_status(surfaces: list[AgenticSurface], *, probed: bool) -> AgenticStatus:
    """Three-state agentic status (spec §7, plan §7.1) — pure, deterministic.

    - no_surface — neither a vendor nor a low-confidence generic input.
    - tested — a surface was detected AND the probe ran (payloads + judge).
    - detected_not_tested — a surface exists but was not probed (gov passive /
      probe could not run). Badge "IA detectada, sin auditar" downstream.
    """
    if not surfaces:
        return AgenticStatus.NO_SURFACE
    if probed:
        return AgenticStatus.TESTED
    return AgenticStatus.DETECTED_NOT_TESTED


def _should_probe(level: str, is_gov: bool) -> bool:
    """Whether active probing is permitted for this (level, is_gov) (spec §1, §3).

    Active payloads only from ``intermedio`` up, and NEVER on a gov automatic /
    passive scan. The 05 wiring is the primary gate (it withholds the probe tool
    on the gov-passive path); this is the defensive in-module guard so a stray
    call still cannot fire payloads on ``.gob.mx``.
    """
    if is_gov:
        return False
    norm = str(level).lower()
    return norm in (ScanLevel.INTERMEDIO.value, ScanLevel.AVANZADO.value)


def _demo_hosts() -> frozenset[str]:
    extra = getattr(settings, "AGENTIC_ALLOWED_DEMO_HOSTS", None)
    if isinstance(extra, str) and extra:
        return _DEFAULT_DEMO_HOSTS | frozenset(
            h.strip() for h in extra.split(",") if h.strip()
        )
    if isinstance(extra, (list, tuple, set, frozenset)):
        return _DEFAULT_DEMO_HOSTS | frozenset(str(h) for h in extra)
    return _DEFAULT_DEMO_HOSTS


async def _probe_surface(
    surface: AgenticSurface,
    *,
    level: str,
    bridge: Any,
    judge_model: Any | None,
    cancel: Any | None,
    emit: Any | None,
) -> tuple[list[Finding], str | None]:
    """Run the capped payload battery against one surface; return findings + a
    probe reply usable for model inference (spec §3.2/§5)."""
    findings: list[Finding] = []
    last_reply: str | None = None

    await bridge.open_widget(surface.launcher_selectors)

    for payload in load_payloads(level):
        if cancel is not None and await cancel.is_set():
            logger.info("agentic.probe.cancelled_between_payloads")
            break
        token = new_canary_token()
        bound = inject_canary(payload, token)
        if emit is not None:
            await emit.tool_start(
                f"Probando técnica '{bound.technique}'", tool="agentic-bridge"
            )
        reply = await bridge.send_and_read(bound.text, input_selectors=())
        last_reply = reply or last_reply
        verdict = judge_response(bound, reply, judge_model)
        if emit is not None:
            await emit.tool_end(
                f"Técnica '{bound.technique}': "
                f"{'comprometido' if verdict.pass_ else 'sin compromiso'}",
                tool="agentic-bridge",
            )
        if verdict.pass_:
            finding = verdict_to_finding(
                bound, reply, verdict, location_url=surface.location_url
            )
            findings.append(finding)
            if emit is not None:
                await emit.finding(finding.title, severity=finding.severity)

    return findings, last_reply


async def agentic_probe(
    target: str,
    *,
    level: str = "basico",
    is_gov: bool = False,
    cancel: Any | None = None,
    emit: Any | None = None,
    host_shared_dir: str = "",
    bridge_factory: BridgeFactory | None = None,
    classifier: Any | None = None,
    judge_model: Any | None = None,
) -> AgenticResult:
    """Detect → (gate) probe → judge → assemble ONE ``AgenticResult`` (the 05 seam).

    ``bridge_factory`` / ``classifier`` / ``judge_model`` are injection points for
    tests (no real browser / API). In production they default to the real
    ``PlaywrightBridge`` and the ``ModelFactory`` Sonnet judge (lazy-imported).
    """
    if emit is not None:
        await emit.agent_status(
            "Superficie agéntica: detectando chatbots / entradas de IA",
            agent=AGENTIC_AGENT_NAME,
        )

    factory = bridge_factory or _default_bridge_factory
    surfaces: list[AgenticSurface] = []
    findings: list[Finding] = []
    inferred: str | None = None
    probed = False
    probe_reply: str | None = None
    network: list[Any] = []

    try:
        async with factory(target=target, cancel=cancel) as bridge:
            snapshot = await bridge.capture_dom(resolve_lazy=True)
            network = list(snapshot.network)
            surfaces = await detect_surface(
                snapshot.dom,
                snapshot.network,
                window_globals=snapshot.window_globals,
                location_url=snapshot.location_url or target,
                classifier=classifier,
            )
            if surfaces and _should_probe(level, is_gov):
                model = judge_model if judge_model is not None else _default_judge_model()
                for surface in surfaces:
                    s_findings, s_reply = await _probe_surface(
                        surface,
                        level=level,
                        bridge=bridge,
                        judge_model=model,
                        cancel=cancel,
                        emit=emit,
                    )
                    findings.extend(s_findings)
                    probe_reply = s_reply or probe_reply
                probed = True
    except Exception as exc:  # noqa: BLE001 - the carril never crashes the scan
        logger.warning("agentic.probe.failed", extra={"target": target, "error": str(exc)})

    inferred = infer_model(network, probe_reply)
    status = decide_status(surfaces, probed=probed)
    primary = surfaces[0] if surfaces else None

    return AgenticResult(
        type=primary.type if primary else "chatbot",
        vendor=primary.vendor if primary else None,
        location_url=primary.location_url if primary else target,
        inferred_model=inferred,
        agentic_status=status.value,
        findings=findings,
    )


def _default_bridge_factory(*, target: str, cancel: Any | None) -> PlaywrightBridge:
    """Real bridge factory — allow-lists the planted demo host for loopback."""
    return PlaywrightBridge(
        target=target, cancel=cancel, allowed_demo_hosts=_demo_hosts()
    )


def _default_judge_model() -> Any | None:
    """The real Sonnet judge wrapper (lazy ModelFactory). ``None`` ⇒ no-leak path.

    Built lazily so importing this module never imports agno/anthropic. When no
    API key is configured the judge falls back to a deterministic non-leak verdict
    (see ``judge.py``).
    """
    try:
        from src.scans.worker.agentic.llm_judge import build_judge_model  # noqa: PLC0415

        return build_judge_model()
    except Exception:  # noqa: BLE001 - no judge ⇒ deterministic non-leak verdicts
        logger.info("agentic.probe.no_judge_model")
        return None


#: The async callable 05 plugs into the seam (DI or DEFAULT_AGENTIC_PROBE override).
AgenticProbeImpl: Callable[..., Awaitable[AgenticResult]] = agentic_probe
