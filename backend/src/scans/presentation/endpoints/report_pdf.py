"""``GET /scans/{id}/report.pdf`` — owner-only PDF (12-api; render owned by 09).

12-api owns only the owner-check (404 for non-owner via ``require_scan_owner``);
the PDF render + redaction belong to 09-reporting. Until 09 plugs in, this returns
425 Too Early if the scan is not finished, else raises ``NotImplementedError`` for
09 to supply the bytes streaming.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from src.common.domain.enums.scans import ScanStatus
from src.common.infrastructure.dependencies.ownership import require_scan_owner
from src.scans.domain.models.scan import Scan

_TERMINAL_STATUSES = {
    str(ScanStatus.DONE),
    str(ScanStatus.PARTIAL),
    str(ScanStatus.FAILED),
    str(ScanStatus.CANCELLED),
}


async def report_pdf(
    scan: Annotated[Scan, Depends(require_scan_owner)],
):
    """Owner-gated PDF. Render is supplied by 09-reporting."""
    if scan.status not in _TERMINAL_STATUSES:
        # Scan still running — the report is not ready yet (plan §9.3, 425/409 TBC w/ 09).
        raise HTTPException(status_code=425, detail="Report not ready yet.")

    raise NotImplementedError(
        "PDF render + redaction is provided by 09-reporting; "
        f"this declaration authorized scan={scan.uuid}."
    )
