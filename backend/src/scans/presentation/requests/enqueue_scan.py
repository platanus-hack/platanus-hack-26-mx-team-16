"""``POST /scans`` request body (12-api §2)."""

from __future__ import annotations

from src.common.domain.entities.common.requests import CamelCaseRequest
from src.common.domain.enums.scans import ScanLevel


class EnqueueScanRequest(CamelCaseRequest):
    url: str
    level: ScanLevel = ScanLevel.BASICO
    # Attestation for active (intrusive) levels — accepted as ``authorized`` or the
    # camelCase ``authorized`` alias; passed to the 01-legal attestation gate.
    authorized: bool = False
