"""``parse_nuclei`` — Nuclei JSONL -> ``list[Finding]`` (spec §2.2, plan §2.1).

Nuclei ``-jsonl`` is the highest-density, demo-critical source: almost 1:1 to the
``Finding`` contract. Each line is one finding. The mapping is **deterministic
Python**, never the LLM:

- ``info.severity`` -> ``severity`` (unknown -> ``info``).
- ``info.classification.cvss-score`` -> ``cvss``.
- ``info.classification.cwe-id`` / ``info.tags`` -> OWASP ``category`` via the
  static ``owasp_map`` (CWE first, then tag, then ``A05`` default).
- ``matched-at`` / ``host`` -> ``affected_url``; ``template-id`` -> tool detail.

A malformed line is skipped (logged), never fatal: a bad line must not lose the
good findings already parsed (partial-failure ethos). Empty input -> ``[]``.
"""

from __future__ import annotations

import json
from typing import Any

from src.common.application.logging import get_logger
from src.scans.domain.contracts.finding import Finding
from src.scans.worker.parsers import owasp_map

logger = get_logger(__name__)

#: nuclei severities map 1:1 to the contract except "unknown"/"" -> info.
_SEVERITY_MAP: dict[str, str] = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "info": "info",
    "unknown": "info",
}


def _severity(raw: str | None) -> str:
    return _SEVERITY_MAP.get((raw or "").strip().lower(), "info")


def _confidence(severity: str, cvss: float | None) -> str:
    """nuclei matches are template-driven, so confidence is high by default.

    A pure ``info`` finding with no CVSS is downgraded to ``media`` (it is often a
    fingerprint, not a confirmed weakness).
    """
    if severity == "info" and cvss is None:
        return "media"
    return "alta"


def _cvss(classification: dict[str, Any] | None) -> float | None:
    if not classification:
        return None
    raw = classification.get("cvss-score")
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _cwe_first(classification: dict[str, Any] | None) -> Any:
    if not classification:
        return None
    cwe = classification.get("cwe-id")
    if isinstance(cwe, list):
        return cwe[0] if cwe else None
    return cwe


def _affected_url(entry: dict[str, Any]) -> str | None:
    return entry.get("matched-at") or entry.get("matched_at") or entry.get("host") or entry.get("url")


def _finding_from_entry(entry: dict[str, Any]) -> Finding | None:
    info = entry.get("info") or {}
    classification = info.get("classification") or {}
    severity = _severity(info.get("severity"))
    cvss = _cvss(classification)
    template_id = entry.get("template-id") or entry.get("templateID") or "nuclei"
    tags = info.get("tags") or []
    if isinstance(tags, str):
        tags = [t for t in tags.split(",") if t]

    category = owasp_map.web_category(cwe=_cwe_first(classification), tags=tags)
    title = info.get("name") or template_id
    description = info.get("description") or title
    affected = _affected_url(entry)
    references = info.get("reference") or []
    if isinstance(references, str):
        references = [references]

    remediation = info.get("remediation") or (
        "Revisa y corrige la condición detectada por la plantilla "
        f"'{template_id}' de Nuclei."
    )

    return Finding(
        source="owasp",
        tool="nuclei",
        category=category,
        title=str(title),
        severity=severity,
        cvss=cvss,
        confidence=_confidence(severity, cvss),
        description=str(description),
        evidence={
            "template_id": template_id,
            "matcher_name": entry.get("matcher-name"),
            "extracted_results": entry.get("extracted-results"),
            "type": entry.get("type"),
            "curl_command": entry.get("curl-command"),
        },
        affected_url=affected,
        endpoint=entry.get("path"),
        impact=(
            f"Nuclei confirmó '{title}'. Un atacante podría explotar esta "
            "condición según la severidad indicada."
        ),
        remediation=str(remediation),
        references=[str(r) for r in references],
    )


def parse_nuclei(stdout: str) -> list[Finding]:
    """Parse Nuclei ``-jsonl`` stdout into ``list[Finding]`` (deterministic).

    One JSON object per line. Blank/malformed lines are skipped (logged). Returns
    ``[]`` for empty input. The category is assigned by the static OWASP map, never
    the LLM.
    """
    findings: list[Finding] = []
    if not stdout:
        return findings
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("parse_nuclei.bad_line", extra={"line": line[:200]})
            continue
        if not isinstance(entry, dict):
            continue
        try:
            finding = _finding_from_entry(entry)
        except Exception:  # noqa: BLE001 - one bad entry must not drop the rest
            logger.warning("parse_nuclei.entry_error", extra={"template": entry.get("template-id")})
            continue
        if finding is not None:
            findings.append(finding)
    return findings
