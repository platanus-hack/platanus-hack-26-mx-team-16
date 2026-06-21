"""``parse_security_headers`` — header JSON -> ``list[Finding]`` (spec §2.2).

Consumes the raw JSON of the ``security-headers`` shim (04
``src/scanning/tools/security_headers.py``):
``{url, status, headers:{present...}, missing:[...], grade?}``.

Each missing security header becomes one ``Finding`` mapped to ``A05`` (or ``A02``
for HSTS) via the static ``owasp_map``. Severity is curated per-header (a missing
CSP/HSTS is ``medium``; cosmetic ones are ``low``). If the shim reported an
``error`` (network failure) we return ``[]`` and let the tool wrapper emit the
coverage meta instead. An Observatory-style ``grade`` is surfaced in evidence.

Deterministic Python; malformed input -> ``[]`` + log (never raises).
"""

from __future__ import annotations

import json
from typing import Any

from src.common.application.logging import get_logger
from src.scans.domain.contracts.finding import Finding
from src.scans.worker.parsers import owasp_map

logger = get_logger(__name__)

#: Per-header severity for the *missing* header. High-impact headers (HSTS, CSP,
#: X-Frame-Options) are medium; the rest are low. Never critical/high — a missing
#: header is a hardening gap, not an exploit.
_HEADER_SEVERITY: dict[str, str] = {
    "strict-transport-security": "medium",
    "content-security-policy": "medium",
    "x-frame-options": "medium",
    "x-content-type-options": "low",
    "referrer-policy": "low",
    "permissions-policy": "low",
    "x-xss-protection": "low",
    "cross-origin-opener-policy": "low",
    "cross-origin-resource-policy": "low",
}

_HUMAN_NAME: dict[str, str] = {
    "strict-transport-security": "HSTS (Strict-Transport-Security)",
    "content-security-policy": "Content-Security-Policy",
    "x-frame-options": "X-Frame-Options",
    "x-content-type-options": "X-Content-Type-Options",
    "referrer-policy": "Referrer-Policy",
    "permissions-policy": "Permissions-Policy",
    "x-xss-protection": "X-XSS-Protection",
    "cross-origin-opener-policy": "Cross-Origin-Opener-Policy",
    "cross-origin-resource-policy": "Cross-Origin-Resource-Policy",
}


def _missing_finding(header: str, url: str | None, grade: Any) -> Finding:
    human = _HUMAN_NAME.get(header, header)
    return Finding(
        source="owasp",
        tool="security_headers",
        category=owasp_map.category_for_header(header),
        title=f"Encabezado de seguridad ausente: {human}",
        severity=_HEADER_SEVERITY.get(header, "low"),
        confidence="alta",
        description=(
            f"La respuesta del sitio no incluye el encabezado de seguridad "
            f"'{human}'."
        ),
        evidence={"missing_header": header, "grade": grade},
        affected_url=url,
        impact=(
            "Sin este encabezado, el navegador no aplica una protección que "
            "mitiga ataques comunes (clickjacking, sniffing de tipo MIME, "
            "degradación de TLS)."
        ),
        remediation=f"Configura el servidor web para enviar el encabezado '{human}'.",
        references=[
            "https://owasp.org/www-project-secure-headers/",
        ],
    )


def parse_security_headers(stdout: str) -> list[Finding]:
    """Parse the security-headers shim JSON into ``list[Finding]`` (deterministic).

    One Finding per missing header (A05/A02). Returns ``[]`` if the shim reported a
    network error, if no header is missing, or if the JSON is malformed (logged).
    """
    if not stdout or not stdout.strip():
        return []
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        logger.warning("parse_security_headers.bad_json")
        return []
    if not isinstance(data, dict):
        return []
    if data.get("error"):
        # Network failure → let the tool wrapper raise a coverage meta instead.
        return []

    url = data.get("url")
    grade = data.get("grade")
    missing = data.get("missing") or []
    if not isinstance(missing, list):
        return []

    findings: list[Finding] = []
    for header in missing:
        if not isinstance(header, str):
            continue
        findings.append(_missing_finding(header.strip().lower(), url, grade))
    return findings
