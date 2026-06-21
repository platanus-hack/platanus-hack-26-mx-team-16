"""``parse_testssl`` — testssl.sh JSON -> ``list[Finding]`` (spec §2.2, plan §2.1).

testssl ``--jsonfile`` (``-oJ``) emits a flat array of records, each with ``id``,
``severity`` ("OK"/"INFO"/"LOW"/"MEDIUM"/"HIGH"/"CRITICAL"/"WARN") and ``finding``.
We keep only the records that actually flag a TLS/SSL weakness (severity LOW and
up) and map them to ``A02`` (Cryptographic Failures) by default, or ``A05`` for
header-shaped ids (HSTS) via the static ``owasp_map``.

The mapping is deterministic Python; ``OK``/``INFO``/``WARN`` records are dropped
(they are not weaknesses). Malformed input -> ``[]`` + log (never raises): a
broken testssl run must not crash the worker (plan §9).
"""

from __future__ import annotations

import json
from typing import Any

from src.common.application.logging import get_logger
from src.scans.domain.contracts.finding import Finding
from src.scans.worker.parsers import owasp_map

logger = get_logger(__name__)

#: testssl severity token -> contract severity. OK/INFO/WARN are NOT weaknesses.
_SEVERITY_MAP: dict[str, str] = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
}

#: testssl ids that are really header issues rather than raw crypto.
_HEADER_LIKE_IDS = ("hsts", "header")


def _maps_to_finding(record: dict[str, Any]) -> bool:
    sev = str(record.get("severity", "")).strip().upper()
    return sev in _SEVERITY_MAP


def _category_for(record_id: str) -> str:
    lowered = record_id.lower()
    if any(tok in lowered for tok in _HEADER_LIKE_IDS):
        return owasp_map.category_for_header("strict-transport-security")
    # Everything else in testssl is a crypto/TLS concern -> A02.
    return owasp_map.web_category(cwe=327)  # Broken/Risky Crypto -> A02


def _finding_from_record(record: dict[str, Any]) -> Finding | None:
    sev_token = str(record.get("severity", "")).strip().upper()
    severity = _SEVERITY_MAP.get(sev_token)
    if severity is None:
        return None
    record_id = str(record.get("id", "testssl"))
    finding_text = str(record.get("finding", record_id))
    cve = record.get("cve")
    references = [str(cve)] if cve else []

    return Finding(
        source="owasp",
        tool="testssl",
        category=_category_for(record_id),
        title=f"TLS/SSL: {record_id}",
        severity=severity,
        confidence="alta",
        description=finding_text,
        evidence={"id": record_id, "finding": finding_text, "cwe": record.get("cwe")},
        affected_url=record.get("ip") or record.get("target"),
        impact=(
            "Una configuración TLS/SSL débil permite interceptar o manipular el "
            "tráfico cifrado entre los usuarios y el sitio."
        ),
        remediation=(
            "Ajusta la configuración TLS del servidor: desactiva protocolos/cifrados "
            "obsoletos y habilita encabezados de seguridad como HSTS."
        ),
        references=references,
    )


def _records(stdout: str) -> list[dict[str, Any]]:
    """Accept either a JSON array or JSONL of testssl records."""
    data = json.loads(stdout)
    if isinstance(data, dict):
        # Some testssl versions wrap under "scanResult"/"scanResultLegacy".
        for key in ("scanResult", "scanResultLegacy"):
            inner = data.get(key)
            if isinstance(inner, list):
                flat: list[dict[str, Any]] = []
                for host in inner:
                    if isinstance(host, dict):
                        for v in host.values():
                            if isinstance(v, list):
                                flat.extend(x for x in v if isinstance(x, dict))
                if flat:
                    return flat
        return [data]
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def parse_testssl(stdout: str) -> list[Finding]:
    """Parse testssl JSON stdout into ``list[Finding]`` (deterministic).

    Keeps only LOW+ severity records (weaknesses), maps them to A02/A05 via the
    static map. Empty/malformed input returns ``[]`` (logged), never raises.
    """
    if not stdout or not stdout.strip():
        return []
    try:
        records = _records(stdout)
    except (json.JSONDecodeError, ValueError):
        logger.warning("parse_testssl.bad_json")
        return []

    findings: list[Finding] = []
    for record in records:
        if not _maps_to_finding(record):
            continue
        try:
            finding = _finding_from_record(record)
        except Exception:  # noqa: BLE001 - one bad record must not drop the rest
            logger.warning("parse_testssl.record_error", extra={"id": record.get("id")})
            continue
        if finding is not None:
            findings.append(finding)
    return findings
