"""Coverage meta-finding helper (05-agent-team spec §4, plan §4).

When a tool fails / times out / is blocked by a WAF, ``run_tool`` returns
``ok=False`` + a ``coverage_note``. The worker degrades that into a
**Finding-meta**: ``severity=info`` (weight 0, never affects the score — 07 §2),
``confidence=baja``, ``category=A05``. It leaves a coverage trail in the report
and the live view without inflating or deflating the grade. The flow CONTINUES;
the exception is never propagated (the partial-failure policy).
"""

from __future__ import annotations

from src.common.domain.enums.scans import FindingCategory
from src.scans.domain.contracts.finding import Finding


def coverage_meta(tool: str, note: str | None) -> Finding:
    """Build the low-confidence ``info`` Finding-meta for a tool that did not complete.

    ``note`` is the ``ToolResult.coverage_note`` ("tool X no completó: timeout...").
    The finding is ``source="owasp"`` so it travels the same persistence path; its
    ``info`` severity guarantees zero penalty weight.
    """
    message = note or f"tool {tool} no completó"
    return Finding(
        source="owasp",
        tool=tool,
        category=FindingCategory.A05.value,
        title=f"Cobertura incompleta: {tool}",
        severity="info",
        confidence="baja",
        description=message,
        impact=(
            "El escaneo no pudo completar esta herramienta, por lo que la "
            "cobertura es parcial: pueden existir hallazgos no detectados."
        ),
        remediation=(
            "Reintenta el escaneo. Si persiste, revisa conectividad/WAF hacia el "
            "objetivo o el presupuesto de tiempo del escaneo."
        ),
        evidence={"coverage_note": message},
    )
