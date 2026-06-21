"""Scans HTTP surface (12-api §1.1). Two routers:

- ``scans_router`` (prefix ``/scans``): enqueue/list/read/findings/stream/report/
  share/cancel.
- ``report_router`` (prefix ``/r``): the public, token-gated redacted report.

Endpoints are standalone functions registered with ``add_api_route`` (the repo's
canonical pattern). AuthZ is enforced per-endpoint by the ownership dependencies.
"""

from fastapi import APIRouter

from src.scans.presentation.endpoints.cancel_scan import cancel_scan
from src.scans.presentation.endpoints.enqueue_scan import enqueue_scan
from src.scans.presentation.endpoints.get_report import get_report
from src.scans.presentation.endpoints.get_scan import get_scan
from src.scans.presentation.endpoints.list_findings import list_findings
from src.scans.presentation.endpoints.list_scans import list_scans
from src.scans.presentation.endpoints.public_report import get_public_report
from src.scans.presentation.endpoints.report_pdf import report_pdf
from src.scans.presentation.endpoints.share_scan import share_scan
from src.scans.presentation.endpoints.stream_scan import stream_scan

scans_router = APIRouter(prefix="/scans", tags=["scans"])

scans_router.add_api_route(
    "",
    enqueue_scan,
    methods=["POST"],
    summary="Enqueue a scan (idempotent, attested, rate-limited) — 201/200/422/429",
)
scans_router.add_api_route(
    "",
    list_scans,
    methods=["GET"],
    summary="List the current user's scans (cursor-paginated)",
)
scans_router.add_api_route(
    "/{scan_id}",
    get_scan,
    methods=["GET"],
    summary="Scan status + scores + observability (owner-or-public, 404 on private)",
)
scans_router.add_api_route(
    "/{scan_id}/findings",
    list_findings,
    methods=["GET"],
    summary="Scan findings, severity desc, cursor-paginated (owner-or-public)",
)
scans_router.add_api_route(
    "/{scan_id}/stream",
    stream_scan,
    methods=["GET"],
    summary="SSE live view (declaration; body filled by 10-realtime-live-view)",
)
scans_router.add_api_route(
    "/{scan_id}/report",
    get_report,
    methods=["GET"],
    summary="In-app JSON report (owner-or-public, 404 on private) — exec + findings",
)
scans_router.add_api_route(
    "/{scan_id}/report.pdf",
    report_pdf,
    methods=["GET"],
    summary="Owner-only PDF report (render owned by 09-reporting)",
)
scans_router.add_api_route(
    "/{scan_id}/share",
    share_scan,
    methods=["POST"],
    summary="Mint a public report link → token (owner-only)",
)
scans_router.add_api_route(
    "/{scan_id}/cancel",
    cancel_scan,
    methods=["POST"],
    summary="Cancel a hung scan (owner-only)",
)


# =============================================================================
# Public report router (token-gated, no auth) — GET /r/{token}
# =============================================================================
report_router = APIRouter(prefix="/r", tags=["public-report"])

report_router.add_api_route(
    "/{token}",
    get_public_report,
    methods=["GET"],
    summary="Public redacted report by token (404 unknown / 410 expired-revoked)",
)
