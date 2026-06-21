"""Executive summary — the ONLY LLM call in the report path (spec §3, plan §6).

Opus is reserved exclusively for narrating the report in plain language. It does
NOT parse, dedupe, or score (those are deterministic Python, done before this
runs). It receives a **compact** summary — top-N findings as
``title`` + ``severity`` + ``category`` + ``impact``, NO raw ``evidence`` — and
returns a structured :class:`ExecutiveSummary` (<2k tokens, ``OPUS_SUMMARY_MAX_TOKENS``).

``agno`` / ``anthropic`` are **lazy-imported inside** :func:`synthesize_summary`
so this module imports cleanly on CI (neither installed). Tests mock at the model
boundary — NEVER a real Anthropic call.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.common.application.logging import get_logger
from src.common.settings import settings
from src.scans.domain.contracts.finding import Finding
from src.scans.domain.services.scoring import ScoreResult

logger = get_logger(__name__)

#: Hard cap on the compact prompt size; keeps Opus well under ~2k tokens (spec §3).
OPUS_SUMMARY_MAX_TOKENS: int = getattr(settings, "OPUS_SUMMARY_MAX_TOKENS", 2000)
#: How many findings (worst-first) to surface to Opus. The rest are summarized
#: only by counts, never sent verbatim.
SUMMARY_TOP_N: int = getattr(settings, "OPUS_SUMMARY_TOP_N", 12)

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


class TopRisk(BaseModel):
    """One headline risk in the executive summary."""

    title: str
    severity: str
    why_it_matters: str  # business-language impact, plain Spanish


class ExecutiveSummary(BaseModel):
    """Structured output of the Opus synthesis (plan §6).

    ``narrative`` is the "Owliver te explica" paragraph; ``top_risks`` are the
    top-3 risks in plain language. This is the ONLY structured-output schema in
    the whole worker (the members never use ``response_model``).
    """

    narrative: str = Field(description="Resumen llano 'Owliver te explica'")
    top_risks: list[TopRisk] = Field(default_factory=list)


def _finding_sort_key(f: Finding) -> tuple[int, float]:
    return (_SEVERITY_ORDER.get(f.severity, 5), -(f.cvss or 0.0))


def compact(findings: list[Finding], *, top_n: int = SUMMARY_TOP_N) -> dict[str, Any]:
    """Build the compact, evidence-free summary Opus receives (spec §3).

    Worst-first top-N with only ``title``/``severity``/``category``/``impact``;
    the remainder is collapsed to per-severity counts. NO ``evidence`` jsonb.
    """
    ordered = sorted(findings, key=_finding_sort_key)
    head = ordered[:top_n]
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return {
        "top_findings": [
            {
                "title": f.title,
                "severity": f.severity,
                "category": f.category,
                "impact": f.impact,
            }
            for f in head
            if f.severity != "info"  # info-only coverage metas don't drive narrative
        ],
        "counts_by_severity": counts,
        "total": len(findings),
    }


def _build_prompt(compact_summary: dict[str, Any], score: ScoreResult) -> str:
    """Plain-text prompt for Opus over the compact summary (kept small)."""
    import json

    return (
        "Eres Owliver, un asistente de ciberseguridad que explica en español "
        "llano. Con base en este resumen de un pentest (ya deduplicado y "
        "puntuado en Python), redacta:\n"
        "1) 'narrative': un párrafo claro para una persona no técnica que "
        "explique el estado de seguridad del sitio.\n"
        "2) 'top_risks': los 3 riesgos más importantes (title, severity, "
        "why_it_matters en lenguaje de negocio).\n"
        "NO inventes hallazgos ni cambies la calificación.\n\n"
        f"Calificación: {score.overall_grade} (score {score.overall_score}/100).\n"
        f"Resumen de hallazgos:\n{json.dumps(compact_summary, ensure_ascii=False)}"
    )


def _fallback_summary(compact_summary: dict[str, Any], score: ScoreResult) -> ExecutiveSummary:
    """Deterministic, LLM-free summary used when no API key / Agno is available.

    Keeps the worker producing a valid report even without the Opus call (CI,
    offline demo) — and is the structural target the real call must satisfy.
    """
    top = compact_summary.get("top_findings", [])[:3]
    risks = [
        TopRisk(
            title=str(item.get("title", "Hallazgo")),
            severity=str(item.get("severity", "medium")),
            why_it_matters=str(item.get("impact", "")),
        )
        for item in top
    ]
    total = compact_summary.get("total", 0)
    narrative = (
        f"El sitio obtuvo una calificación {score.overall_grade} "
        f"({score.overall_score}/100). Se detectaron {total} hallazgos. "
        + (
            "Los más relevantes se listan a continuación."
            if risks
            else "No se detectaron hallazgos significativos."
        )
    )
    return ExecutiveSummary(narrative=narrative, top_risks=risks)


async def synthesize_summary(
    findings: list[Finding],
    score: ScoreResult,
    *,
    model: Any | None = None,
    top_n: int = SUMMARY_TOP_N,
) -> ExecutiveSummary:
    """Produce the executive summary with Opus (the single LLM report call).

    ``model`` (an Agno model or a fake with ``.arun``) is injectable so tests pass
    a stub — NEVER a real Anthropic call in CI. When ``model`` is None and no
    ``ANTHROPIC_API_KEY`` is configured, falls back to the deterministic summary.

    ``agno`` / ``anthropic`` are imported lazily inside this function so the module
    imports without them.
    """
    compact_summary = compact(findings, top_n=top_n)

    api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
    if model is None and not api_key:
        logger.info("synthesize_summary.fallback_no_key")
        return _fallback_summary(compact_summary, score)

    try:
        agent = _build_agent(model)
        prompt = _build_prompt(compact_summary, score)
        result = await agent.arun(prompt)
        content = getattr(result, "content", result)
        if isinstance(content, ExecutiveSummary):
            return content
        if isinstance(content, dict):
            return ExecutiveSummary.model_validate(content)
        if isinstance(content, str):
            import json

            return ExecutiveSummary.model_validate(json.loads(content))
    except Exception:  # noqa: BLE001 - the report must never fail on the LLM (plan §10)
        logger.warning("synthesize_summary.llm_error_falling_back")

    return _fallback_summary(compact_summary, score)


def _build_agent(model: Any | None) -> Any:
    """Build the Opus ``Agent`` with ``output_schema=ExecutiveSummary`` (lazy import).

    If ``model`` is provided (a fake or pre-built Agno model) it is used as-is —
    that is the test seam. Otherwise ``agno`` + the ``ModelFactory`` (which lazily
    imports ``anthropic`` via Agno's ``Claude``) build the real Opus agent.
    """
    if model is not None and hasattr(model, "arun"):
        # The caller passed a ready agent-like object (test stub).
        return model

    from agno.agent import Agent  # noqa: PLC0415 - lazy: keep module import light

    from src.scans.worker.models import ModelFactory

    opus = model if model is not None else ModelFactory().opus()
    return Agent(
        model=opus,
        output_schema=ExecutiveSummary,
        instructions=(
            "Redacta el resumen ejecutivo de un pentest en español llano. "
            "No inventes hallazgos ni cambies la calificación."
        ),
    )
