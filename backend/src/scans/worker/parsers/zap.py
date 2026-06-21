"""``parse_zap_baseline`` — ZAP baseline JSON -> ``list[Finding]`` (4th parser).

ZAP ``zap-baseline.py -J report.json`` emits the standard ZAP JSON report:
``{site:[{alerts:[{name, riskcode, confidence, desc, solution, cweid, instances:
[{uri, param, evidence}]}]}]}``. We flatten alerts across sites, map ``riskcode``
(3=high,2=medium,1=low,0=info) to severity, ``cweid`` to OWASP category via the
static ``owasp_map``, and use the first instance for ``affected_url``/``param``.

Deterministic Python; malformed input -> ``[]`` + log (never raises).
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.common.application.logging import get_logger
from src.scans.domain.contracts.finding import Finding
from src.scans.worker.parsers import owasp_map

logger = get_logger(__name__)

#: ZAP riskcode -> contract severity. ZAP has no "critical" band; 3 == high.
_RISK_MAP: dict[str, str] = {"3": "high", "2": "medium", "1": "low", "0": "info"}
#: ZAP confidence (0..4 / High..Low) -> contract confidence.
_CONFIDENCE_MAP: dict[str, str] = {
    "3": "alta",
    "4": "alta",
    "2": "media",
    "1": "baja",
    "0": "baja",
    "high": "alta",
    "medium": "media",
    "low": "baja",
}

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    return _TAG_RE.sub("", text).strip()


def _severity(riskcode: Any) -> str:
    return _RISK_MAP.get(str(riskcode).strip(), "info")


def _confidence(value: Any) -> str:
    return _CONFIDENCE_MAP.get(str(value).strip().lower(), "media")


def _finding_from_alert(alert: dict[str, Any]) -> Finding | None:
    name = alert.get("name") or alert.get("alert") or "ZAP alert"
    severity = _severity(alert.get("riskcode"))
    instances = alert.get("instances") or []
    first = instances[0] if instances and isinstance(instances[0], dict) else {}
    cweid = alert.get("cweid")

    return Finding(
        source="owasp",
        tool="zap_baseline",
        category=owasp_map.web_category(cwe=cweid),
        title=str(name),
        severity=severity,
        confidence=_confidence(alert.get("confidence")),
        description=_strip_html(alert.get("desc")) or str(name),
        evidence={
            "pluginid": alert.get("pluginid"),
            "cweid": cweid,
            "wascid": alert.get("wascid"),
            "evidence": first.get("evidence"),
            "instances": len(instances),
        },
        affected_url=first.get("uri") or alert.get("url"),
        param=first.get("param") or None,
        impact=(
            f"ZAP detectó '{name}'. Según la severidad, puede exponer datos o "
            "permitir manipular el comportamiento del sitio."
        ),
        remediation=_strip_html(alert.get("solution"))
        or "Aplica la mitigación recomendada por ZAP para esta alerta.",
        references=[r for r in [_strip_html(alert.get("reference"))] if r],
    )


def parse_zap_baseline(stdout: str) -> list[Finding]:
    """Parse a ZAP baseline JSON report into ``list[Finding]`` (deterministic).

    Flattens ``site[].alerts[]``. Returns ``[]`` for empty/malformed input
    (logged). ``info`` alerts are kept (weight 0, but visible in the report).
    """
    if not stdout or not stdout.strip():
        return []
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        logger.warning("parse_zap_baseline.bad_json")
        return []
    if not isinstance(data, dict):
        return []

    sites = data.get("site") or data.get("sites") or []
    if isinstance(sites, dict):
        sites = [sites]

    findings: list[Finding] = []
    for site in sites:
        if not isinstance(site, dict):
            continue
        for alert in site.get("alerts") or []:
            if not isinstance(alert, dict):
                continue
            try:
                finding = _finding_from_alert(alert)
            except Exception:  # noqa: BLE001 - one bad alert must not drop the rest
                logger.warning("parse_zap_baseline.alert_error")
                continue
            if finding is not None:
                findings.append(finding)
    return findings
