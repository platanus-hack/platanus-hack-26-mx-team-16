"""In-app report presenter — the **flat** JSON contract the web report consumes.

``GET /scans/{id}/report`` (the authenticated "Owliver te explica" screen, §F7)
renders a *flat* DTO: ``{ scan, explanation, topRisks, surfaces, findings }``
(frontend ``reportSchema`` in ``schemas/api.ts``). This is intentionally a
**different** shape from :class:`~src.scans.presentation.presenters.report.ReportPresenter`,
which emits the *nested* ``{ executive, technical, meta }`` dict the PDF renderer
(09-reporting) consumes.

The two contracts drifted apart because the web report and the PDF were built to
separate specs and only the PDF/public surfaces had an endpoint; the in-app JSON
endpoint was missing, so the web report always 404'd and fell back to the demo
fixture. This presenter is the single mapping from persisted scan data → the web
contract. (Reconciling both surfaces onto one DTO is tracked as tech debt.)

Like every report surface it is **read-only**: it never re-calls the LLM nor
re-computes the score — it projects what the worker already persisted (07 owns
scoring, 05 owns the Opus ``ExecutiveSummary`` in ``scan.summary``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.common.presentation.pagination import severity_rank
from src.scans.domain.models.agentic_surface import AgenticSurface
from src.scans.domain.models.finding import FindingRecord
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.finding import FindingPresenter
from src.scans.presentation.presenters.scan import ScanDetailPresenter


def _explanation(scan: Scan) -> str:
    """The Opus "Owliver te explica" paragraph from the persisted summary (05 §6).

    ``scan.summary`` is the JSONB ``ExecutiveSummary`` (``narrative`` +
    ``top_risks[]``). Defaults to ``""`` so the (required) frontend field is
    always a string, even before the summary phase has run.
    """
    return (scan.summary or {}).get("narrative") or ""


def _top_risks(scan: Scan) -> list[dict[str, str]]:
    """Top-3 prioritized risks → ``{ title, impact }`` (frontend ``reportSchema``).

    The persisted ``TopRisk`` carries ``why_it_matters``; the web report labels
    that field ``impact``.
    """
    summary = scan.summary or {}
    risks = summary.get("top_risks") or summary.get("topRisks") or []
    return [
        {
            "title": risk.get("title") or "",
            "impact": (
                risk.get("why_it_matters")
                or risk.get("whyItMatters")
                or risk.get("impact")
                or ""
            ),
        }
        for risk in risks
    ]


def _surfaces(scan: Scan, surfaces: list[AgenticSurface]) -> list[dict[str, Any]]:
    """Agentic-surface inventory → frontend ``agenticSurfaceSchema``.

    ``AgenticSurface`` has no per-surface coverage column, so the scan-level
    ``agentic_status`` is the authoritative state for the whole inventory; it
    falls back to ``detected_not_tested`` (a surface exists but the run did not
    record a status).
    """
    status = scan.agentic_status or "detected_not_tested"
    return [
        {
            "type": s.type,
            "vendor": s.vendor,
            "locationUrl": s.location_url,
            "inferredModel": s.inferred_model,
            "agenticStatus": status,
        }
        for s in surfaces
    ]


@dataclass
class ReportViewPresenter:
    """Compose the flat web-report dict (``reportSchema``) from persisted data.

    This is the **authenticated owner** view: findings carry full ``evidence``
    (via :class:`FindingPresenter`). The public ``/r/{token}`` surface redacts
    evidence through its own path.
    """

    scan: Scan
    host: str | None = None
    findings: list[FindingRecord] = field(default_factory=list)
    agentic_surfaces: list[AgenticSurface] = field(default_factory=list)

    @property
    def to_dict(self) -> dict[str, Any]:
        ordered = sorted(
            self.findings, key=lambda f: (severity_rank(f.severity), str(f.uuid))
        )
        findings: list[dict[str, Any]] = []
        for f in ordered:
            d = FindingPresenter(f).to_dict
            # Frontend ``findingSchema`` keys the accordion on ``id``; the rest
            # of the (camelCase) fields pass through untouched.
            d["id"] = d.pop("findingId")
            findings.append(d)

        return {
            "scan": ScanDetailPresenter(self.scan, host=self.host).to_dict,
            "explanation": _explanation(self.scan),
            "topRisks": _top_risks(self.scan),
            "surfaces": _surfaces(self.scan, self.agentic_surfaces),
            "findings": findings,
        }
