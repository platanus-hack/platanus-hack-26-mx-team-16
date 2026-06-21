"""``GET /scans/{id}/report.pdf`` — owner-only PDF (12-api owner-check; render 09).

12-api owns the owner-check (404 for non-owner via ``require_scan_owner``) and the
425-if-not-terminal guard; 09-reporting fills the PDF render. The owner report is
**not** redacted — the owner sees full evidence (redaction is only for the public
``/r/{token}`` link). The render engine is lazy-imported inside ``render_report_pdf``
so this module imports even when no PDF library is installed; if the configured
``PDF_ENGINE`` is missing its dependency the request fails with 503 rather than a
500 (the PDF is a recortable M3 deliverable — spec §4.1).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.responses import Response

from src.common.domain.enums.scans import ScanStatus
from src.common.infrastructure.dependencies.common import DomainContextDep
from src.common.infrastructure.dependencies.ownership import require_scan_owner
from src.common.settings import settings
from src.scans.domain.models.scan import Scan
from src.scans.presentation.presenters.report import ReportPresenter

_TERMINAL_STATUSES = {
    str(ScanStatus.DONE),
    str(ScanStatus.PARTIAL),
    str(ScanStatus.FAILED),
    str(ScanStatus.CANCELLED),
}


async def report_pdf(
    domain_context: DomainContextDep,
    scan: Annotated[Scan, Depends(require_scan_owner)],
) -> Response:
    """Owner-gated PDF of the (non-redacted) report."""
    if scan.status not in _TERMINAL_STATUSES:
        # Scan still running — the report is not ready yet (425 Too Early).
        raise HTTPException(status_code=425, detail="Report not ready yet.")

    findings = await domain_context.finding_repository.list_for_scan(scan.uuid)
    report = ReportPresenter(scan=scan, findings=findings, public=False).to_dict

    # Lazy import: the render module pulls in the heavy PDF engine only when
    # invoked, so this endpoint module imports cleanly without the dependency.
    from src.scans.infrastructure.pdf.render import PdfEngineError, render_report_pdf

    # ``STATIC_BASE_URL`` is added via settingsAdditions; default safely so this
    # works before the orchestrator patches settings.py.
    base_url = str(getattr(settings, "STATIC_BASE_URL", "") or "http://localhost:8200")
    try:
        pdf_bytes = render_report_pdf(report, base_url=base_url)
    except PdfEngineError as exc:
        # PDF is a recortable M3 deliverable; surface a clean 503 if the engine
        # dependency is not installed instead of a 500.
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    filename = f"owliver-report-{scan.uuid}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
