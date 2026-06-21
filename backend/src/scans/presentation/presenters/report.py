"""Report content assembly — the two-layer report DTO (09-reporting §3 / spec §2).

A single :class:`ReportPresenter` composes the **executive layer** (A–F grade,
two sub-scores, Opus "Owliver te explica" narrative, top-3 risks, agentic-surface
inventory, badges) and the **technical layer** (per-finding accordion, available
filters, historical trend) from what the worker already persisted — it never
re-calls the LLM nor re-computes the score (07 owns scoring).

The **only** difference between the authenticated owner report and the public
``/r/{token}`` report is a single ``public: bool`` flag that flips every finding
through :func:`redact_finding`. There is exactly one assembly path, so the public
report can never accidentally skip redaction (09 §1).

The PDF renderer and the frontend consume the same dict shape this presenter
emits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.common.domain.enums.scans import AgenticStatus, ScanStatus
from src.common.presentation.pagination import severity_rank
from src.scans.domain.models.agentic_surface import AgenticSurface
from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.redaction import redact_finding

#: Badge copy (spec §2.1). Computed in Python from columns, NEVER from the LLM.
BADGE_AGENTIC_DETECTED_UNTESTED = "IA detectada, sin auditar"
BADGE_PARTIAL_COVERAGE = "cobertura parcial"


def _executive_badges(scan: Scan) -> list[str]:
    """Status badges derived from persisted columns (spec §2.1).

    - "IA detectada, sin auditar" when ``agentic_status == detected_not_tested``.
    - "cobertura parcial" when the scan finished partial (grade capped at C, 07).
    """
    badges: list[str] = []
    if scan.agentic_status == str(AgenticStatus.DETECTED_NOT_TESTED):
        badges.append(BADGE_AGENTIC_DETECTED_UNTESTED)
    if scan.status == str(ScanStatus.PARTIAL):
        badges.append(BADGE_PARTIAL_COVERAGE)
    return badges


def _top_risks(scan: Scan) -> list[dict[str, Any]]:
    """The top-3 prioritized risks from the persisted Opus ``ExecutiveSummary``.

    ``scan.summary`` is the JSONB ``ExecutiveSummary`` (05 §6): ``narrative`` +
    ``top_risks[]`` (``title``/``severity``/``why_it_matters``). Read-only here.
    """
    summary = scan.summary or {}
    risks = summary.get("top_risks") or summary.get("topRisks") or []
    return [
        {
            "title": risk.get("title"),
            "severity": risk.get("severity"),
            "whyItMatters": risk.get("why_it_matters") or risk.get("whyItMatters"),
        }
        for risk in risks
    ]


def _agentic_surface(surfaces: list[AgenticSurface]) -> list[dict[str, Any]]:
    """The detected agentic-surface inventory (spec §2.1 / 03-agentic-surface)."""
    return [
        {
            "type": s.type,
            "vendor": s.vendor,
            "locationUrl": s.location_url,
            "inferredModel": s.inferred_model,
        }
        for s in surfaces
    ]


def _available_filters(findings: list[FindingRecord]) -> dict[str, list[str]]:
    """Distinct severities / sources / categories present in this scan (spec §2.2).

    Sorted deterministically (severity by rank, the rest lexicographically) so the
    UI filter chips render in a stable order.
    """
    severities = sorted({f.severity for f in findings}, key=severity_rank)
    sources = sorted({f.source for f in findings})
    categories = sorted({f.category for f in findings})
    return {"severities": severities, "sources": sources, "categories": categories}


def _trend(findings: list[FindingRecord], scan: Scan) -> dict[str, int]:
    """Historical trend counts derived from persisted lifecycle fields (spec §2.2).

    A finding is *new* when its ``first_seen`` equals the scan's ``finished_at``
    (first appeared in this scan); it is *fixed* when ``status == "fixed"``. The
    dedupe mechanics live in 06/08; here it is only presented.
    """
    finished = scan.finished_at
    new = sum(
        1
        for f in findings
        if finished is not None and f.first_seen == finished
    )
    fixed = sum(1 for f in findings if f.status == "fixed")
    return {"new": new, "fixed": fixed}


@dataclass
class ReportPresenter:
    """Compose the two-layer report dict from persisted scan data.

    ``public=False`` → authenticated owner report (full ``evidence``).
    ``public=True``  → public ``/r/{token}`` report (``evidence`` redacted).
    """

    scan: Scan
    findings: list[FindingRecord] = field(default_factory=list)
    agentic_surfaces: list[AgenticSurface] = field(default_factory=list)
    public: bool = False

    @property
    def to_dict(self) -> dict[str, Any]:
        scan = self.scan
        ordered = sorted(
            self.findings, key=lambda f: (severity_rank(f.severity), str(f.uuid))
        )
        summary = scan.summary or {}

        executive = {
            "overallGrade": scan.overall_grade,
            "overallScore": scan.overall_score,
            "webScore": scan.web_score,
            # null (not 0) when there is no auditable agentic surface — the UI
            # renders the "IA detectada, sin auditar" badge instead of a number.
            "agenticScore": scan.agentic_score,
            "agenticStatus": scan.agentic_status,
            "narrative": summary.get("narrative"),
            "topRisks": _top_risks(scan),
            "agenticSurface": _agentic_surface(self.agentic_surfaces),
            "badges": _executive_badges(scan),
        }

        technical = {
            "findings": [
                redact_finding(f, public=self.public) for f in ordered
            ],
            "filters": _available_filters(ordered),
            "trend": _trend(ordered, scan),
        }

        meta = {
            "scanId": str(scan.uuid),
            "siteId": str(scan.site_id),
            "level": scan.level,
            "status": scan.status,
            "coveragePartial": scan.status == str(ScanStatus.PARTIAL),
            "finishedAt": scan.finished_at,
        }

        return {
            "executive": executive,
            "technical": technical,
            "meta": meta,
            "redacted": self.public,
        }


@dataclass
class PublicReportPresenter:
    """The public ``/r/{token}`` report — identical executive layer, redacted
    technical layer. Thin wrapper that pins ``public=True`` so the redaction can
    never be skipped (09 §1)."""

    scan: Scan
    findings: list[FindingRecord] = field(default_factory=list)
    agentic_surfaces: list[AgenticSurface] = field(default_factory=list)

    @property
    def to_dict(self) -> dict[str, Any]:
        return ReportPresenter(
            scan=self.scan,
            findings=self.findings,
            agentic_surfaces=self.agentic_surfaces,
            public=True,
        ).to_dict
