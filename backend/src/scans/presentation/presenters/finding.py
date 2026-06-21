"""Finding presenter — ``FindingRecord`` → camelCase (12-api §"Lectura").

This is the **authenticated** (owner) view: it includes ``evidence``. The public
``/r/{token}`` surface uses :class:`RedactedFindingPresenter` instead, which never
emits raw exploit payloads (spec §11.3 / 09-reporting).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.common.domain.interfaces.presenter import Presenter
from src.scans.domain.models.finding import FindingRecord


@dataclass
class FindingPresenter(Presenter[FindingRecord]):
    instance: FindingRecord

    @property
    def to_dict(self) -> dict[str, Any]:
        f = self.instance
        return {
            "findingId": str(f.uuid),
            "scanId": str(f.scan_id),
            "siteId": str(f.site_id),
            "source": f.source,
            "tool": f.tool,
            "category": f.category,
            "title": f.title,
            "severity": f.severity,
            "cvss": f.cvss,
            "confidence": f.confidence,
            "description": f.description,
            "evidence": f.evidence,
            "affectedUrl": f.affected_url,
            "endpoint": f.endpoint,
            "param": f.param,
            "impact": f.impact,
            "remediation": f.remediation,
            "references": f.references,
            "status": f.status,
            "firstSeen": f.first_seen,
            "lastSeen": f.last_seen,
        }


@dataclass
class RedactedFindingPresenter(Presenter[FindingRecord]):
    """Public-report finding — type/category/severity/impact/remediation only,
    NEVER the raw exploit (no ``evidence``, ``param`` or ``affected_url``).

    The full redaction/render is owned by 09-reporting; this is the safe-by-
    default projection the ``/r/{token}`` endpoint serves until 09 plugs in."""

    instance: FindingRecord

    @property
    def to_dict(self) -> dict[str, Any]:
        f = self.instance
        return {
            "category": f.category,
            "title": f.title,
            "severity": f.severity,
            "confidence": f.confidence,
            "impact": f.impact,
            "remediation": f.remediation,
        }
