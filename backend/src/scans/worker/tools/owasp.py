"""OWASP tool-function wrappers — parser INSIDE the closure (spec §2, plan §2).

Each wrapper is a Python callable registered on the OWASP Sonnet agent. It does
NOT spawn processes and does NOT decide policy: it calls ``run_tool`` (04), parses
the raw ``stdout`` into ``list[Finding]`` with the deterministic parser (this
feature), pushes them into the shared ``session_state`` via ``accumulate``, emits
``tool_start``/``tool_end`` live events, and returns a SHORT string the LLM uses to
pick the next step. The findings never travel through an LLM message (that is the
whole point — keep the model out of the data path).

The wrappers are built by ``make_run_*`` **closures** that capture the per-scan
context (``target``, ``host_shared_dir``, ``cancel``, ``emit``) so the LLM only
ever invokes them with no arguments. ``build_owasp_tools(...)`` returns the set of
wrappers enabled for the resolved tool battery (``resolve_tools`` already applied
the 02 whitelist), so a tool the level forbids is never even constructed.

On ``ToolResult.ok is False`` (timeout / non-zero / WAF / exception inside
``run_tool``) the wrapper accumulates a low-confidence **coverage Finding-meta**
(``severity=info``) and records ``coverage[tool]=failed|timeout`` — the flow
CONTINUES, the exception is never propagated (the partial-failure policy, §4).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from src.common.application.logging import get_logger
from src.scanning import CancelToken, ToolResult, run_tool, spec_for
from src.scans.domain.contracts.finding import Finding
from src.scans.domain.enums.tool_id import ToolId
from src.scans.worker.events import ScanEventEmitter
from src.scans.worker.parsers._meta import coverage_meta
from src.scans.worker.parsers.generic import parse_nikto, parse_sqlmap
from src.scans.worker.parsers.nuclei import parse_nuclei
from src.scans.worker.parsers.security_headers import parse_security_headers
from src.scans.worker.parsers.testssl import parse_testssl
from src.scans.worker.parsers.zap import parse_zap_baseline
from src.scans.worker.tools._accumulate import accumulate

logger = get_logger(__name__)

#: A parser takes raw stdout (+ optional affected_url) and returns ``Finding[]``.
Parser = Callable[..., list[Finding]]

#: Mapping ToolId -> deterministic parser. Tools without a dedicated parser fall
#: through to the generic best-effort handlers; tools not here run but produce
#: only a coverage trace (no findings) — they are recon helpers (whatweb, etc).
_PARSERS: dict[ToolId, Parser] = {
    ToolId.NUCLEI: parse_nuclei,
    ToolId.TESTSSL: parse_testssl,
    ToolId.SECURITY_HEADERS: parse_security_headers,
    ToolId.ZAP_BASELINE: parse_zap_baseline,
    ToolId.NIKTO: parse_nikto,
    ToolId.SQLMAP: parse_sqlmap,
}

#: Human-readable tool descriptions used as the docstring the LLM reads. The
#: actual selection is bounded by ``resolve_tools`` (02 whitelist) regardless.
_DESCRIPTIONS: dict[ToolId, str] = {
    ToolId.NUCLEI: "Ejecuta Nuclei (plantillas OWASP web). Úsalo en todos los niveles.",
    ToolId.TESTSSL: "Audita la configuración TLS/SSL del objetivo.",
    ToolId.SECURITY_HEADERS: "Revisa los encabezados de seguridad HTTP.",
    ToolId.WHATWEB: "Identifica tecnologías del sitio (fingerprinting).",
    ToolId.ZAP_BASELINE: "Escaneo pasivo OWASP ZAP (baseline).",
    ToolId.NIKTO: "Escáner de configuración/servidor web (best-effort).",
    ToolId.SQLMAP: "Prueba de inyección SQL (best-effort, solo niveles activos).",
    ToolId.SUBFINDER: "Enumera subdominios del objetivo.",
    ToolId.KATANA: "Rastrea (crawl) el sitio para descubrir endpoints.",
    ToolId.FFUF: "Fuerza bruta de directorios/archivos.",
    ToolId.DNSX: "Resolución y sondeo DNS.",
}

ToolFn = Callable[..., Awaitable[str]]


def _parser_for(tool: ToolId) -> Parser | None:
    return _PARSERS.get(tool)


def _findings_from_result(tool: ToolId, result: ToolResult, *, target: str) -> list[Finding]:
    """Parse a successful result, or build the coverage meta on failure (§4)."""
    if not result.ok:
        return [coverage_meta(str(tool), result.coverage_note)]
    parser = _parser_for(tool)
    if parser is None:
        # Recon-only tool: ran fine but has no finding parser. No meta (it is not a
        # failure), no findings — its value is in fingerprint/coverage, not scoring.
        return []
    try:
        # The generic parsers accept affected_url; the structured ones ignore it.
        return parser(result.stdout, affected_url=target)
    except TypeError:
        return parser(result.stdout)
    except Exception:  # noqa: BLE001 - a parser bug degrades to coverage, never crashes
        logger.warning("owasp_tool.parser_error", extra={"tool": str(tool)})
        return [coverage_meta(str(tool), f"parser de {tool} falló")]


def make_owasp_tool(
    tool: ToolId,
    *,
    target: str,
    host_shared_dir: str,
    cancel: CancelToken,
    emit: ScanEventEmitter,
    flags: tuple[str, ...] = (),
    coverage: dict[str, str] | None = None,
) -> ToolFn:
    """Build the closed-over async tool-function for ``tool`` (spec §2 form).

    The returned callable takes no LLM-supplied arguments; it runs the tool via
    ``run_tool``, parses into ``Finding[]``, accumulates them into
    ``run_context.session_state['findings']``, emits live events, updates the
    shared ``coverage`` dict, and returns a short status string.
    """
    spec = spec_for(tool)
    tool_name = str(tool)
    description = _DESCRIPTIONS.get(tool, f"Ejecuta {tool_name}.")

    async def run(run_context: Any | None = None) -> str:
        await emit.tool_start(f"Ejecutando {tool_name}", tool=tool_name)
        result = await run_tool(
            spec,
            target=target,
            host_shared_dir=host_shared_dir,
            cancel=cancel,
            flags=flags,
        )
        findings = _findings_from_result(tool, result, target=target)
        if run_context is not None:
            accumulate(run_context, findings)
        if coverage is not None:
            if result.ok:
                coverage[tool_name] = "ok"
            elif result.timed_out:
                coverage[tool_name] = "timeout"
            else:
                coverage[tool_name] = "failed"
        await emit.tool_end(
            f"{tool_name}: {len(findings)} hallazgos",
            tool=tool_name,
            payload={"ok": result.ok, "n": len(findings), "duration_s": result.duration_s},
        )
        status = "ok" if result.ok else (result.coverage_note or "falló")
        return f"{tool_name}: {len(findings)} hallazgos ({status})"

    run.__name__ = f"run_{tool_name}"
    run.__doc__ = description
    return run


# -- Named convenience factories (spec §1.1 lists run_nuclei/run_zap/...) --------
# Thin wrappers over make_owasp_tool so callers/tests can reference the canonical
# names from the spec. Each binds its ToolId; signature is otherwise identical.


def _named(tool: ToolId):
    def factory(**kwargs: Any) -> ToolFn:
        return make_owasp_tool(tool, **kwargs)

    factory.__name__ = f"make_run_{tool}"
    return factory


make_run_nuclei = _named(ToolId.NUCLEI)
make_run_testssl = _named(ToolId.TESTSSL)
make_run_security_headers = _named(ToolId.SECURITY_HEADERS)
make_run_zap = _named(ToolId.ZAP_BASELINE)
make_run_whatweb = _named(ToolId.WHATWEB)
make_run_nikto = _named(ToolId.NIKTO)
make_run_sqlmap = _named(ToolId.SQLMAP)
make_run_subfinder = _named(ToolId.SUBFINDER)
make_run_katana = _named(ToolId.KATANA)
make_run_ffuf = _named(ToolId.FFUF)


def build_owasp_tools(
    invocations: list[Any],
    *,
    target: str,
    host_shared_dir: str,
    cancel: CancelToken,
    emit: ScanEventEmitter,
    coverage: dict[str, str] | None = None,
) -> list[ToolFn]:
    """Build the tool-functions for the resolved ``invocations`` (02 whitelist).

    ``invocations`` is the ``list[ToolInvocation]`` from ``resolve_tools`` — each
    carries ``.tool`` (ToolId) and ``.flags``. Returns one closed-over async
    callable per invocation, in order. Anything not resolved is never built
    (allow-list by construction).
    """
    tools: list[ToolFn] = []
    for inv in invocations:
        tools.append(
            make_owasp_tool(
                inv.tool,
                target=target,
                host_shared_dir=host_shared_dir,
                cancel=cancel,
                emit=emit,
                flags=tuple(getattr(inv, "flags", ()) or ()),
                coverage=coverage,
            )
        )
    return tools
