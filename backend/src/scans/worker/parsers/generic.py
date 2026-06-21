"""``parse_generic`` — best-effort text parser for nikto/sqlmap (spec §2.2).

nikto and sqlmap emit unstructured text without a clean severity/OWASP signal.
Per the spec they get a **best-effort** treatment: collapse the run into a small
number of low/medium ``Finding`` rows with ``confidence=baja`` rather than trying
to mine OWASP categories the tool never provides. This keeps their signal in the
report without pretending to a precision the source lacks.

- ``parse_sqlmap``: if the output declares an injectable parameter, emit ONE
  ``high`` A03 (Injection) finding; otherwise ``[]``.
- ``parse_nikto``: emit ONE ``medium`` A05 finding summarizing the item count if
  the run reported any ``+ ...`` items; otherwise ``[]``.

Deterministic Python; never raises (returns ``[]`` on anything unexpected).
"""

from __future__ import annotations

from src.common.application.logging import get_logger
from src.scans.domain.contracts.finding import Finding
from src.scans.worker.parsers import owasp_map

logger = get_logger(__name__)

#: sqlmap prints this when it confirms an injectable parameter.
_SQLMAP_HIT_MARKERS = (
    "is vulnerable",
    "appears to be injectable",
    "the following injection point",
    "sqlmap identified the following injection",
)


def parse_sqlmap(stdout: str, *, affected_url: str | None = None) -> list[Finding]:
    """One ``high`` A03 finding if sqlmap confirmed an injection, else ``[]``."""
    if not stdout:
        return []
    lowered = stdout.lower()
    if not any(marker in lowered for marker in _SQLMAP_HIT_MARKERS):
        return []
    return [
        Finding(
            source="owasp",
            tool="sqlmap",
            category=owasp_map.web_category(cwe=89),  # SQL Injection -> A03
            title="Posible inyección SQL detectada (sqlmap)",
            severity="high",
            confidence="baja",  # text-mined, best-effort (spec §2.2)
            description=(
                "sqlmap reportó al menos un parámetro potencialmente inyectable. "
                "Requiere validación manual antes de confirmarse."
            ),
            evidence={"excerpt": stdout[-1000:]},
            affected_url=affected_url,
            impact=(
                "Una inyección SQL permitiría a un atacante leer o modificar la "
                "base de datos del sitio."
            ),
            remediation=(
                "Usa consultas parametrizadas/prepared statements y valida la "
                "entrada del usuario en todos los parámetros."
            ),
        )
    ]


def parse_nikto(stdout: str, *, affected_url: str | None = None) -> list[Finding]:
    """One ``medium`` A05 summary finding if nikto reported items, else ``[]``."""
    if not stdout:
        return []
    items = [ln.strip() for ln in stdout.splitlines() if ln.strip().startswith("+ ")]
    # Drop nikto's banner/timing "+ " lines that are not findings.
    items = [
        ln
        for ln in items
        if not ln.lower().startswith(("+ target", "+ start time", "+ end time", "+ server:", "+ ssl info"))
    ]
    if not items:
        return []
    return [
        Finding(
            source="owasp",
            tool="nikto",
            category=owasp_map.DEFAULT_WEB_CATEGORY,  # A05 misconfig
            title=f"Nikto reportó {len(items)} observaciones de configuración",
            severity="medium",
            confidence="baja",  # text-mined, best-effort (spec §2.2)
            description=(
                "Nikto encontró posibles problemas de configuración o "
                "componentes expuestos. Revisa el detalle para priorizar."
            ),
            evidence={"items": items[:25], "total": len(items)},
            affected_url=affected_url,
            impact=(
                "Configuraciones inseguras o archivos expuestos facilitan el "
                "reconocimiento y la explotación por parte de un atacante."
            ),
            remediation=(
                "Revisa cada observación de Nikto y corrige las configuraciones "
                "o elimina los recursos expuestos que no deban ser públicos."
            ),
        )
    ]
