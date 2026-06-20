"""Finding factory for scoring tests — builds valid frozen ``Finding`` contracts."""

from __future__ import annotations

from src.scans.domain.contracts.finding import Finding


def make_finding(
    *,
    source: str = "owasp",
    severity: str = "high",
    confidence: str = "alta",
    category: str = "A01",
    tool: str = "nuclei",
    affected_url: str | None = "https://gob.mx/login",
    endpoint: str | None = "/login",
    param: str | None = None,
    title: str = "Finding",
) -> Finding:
    """Build a minimal valid ``Finding`` for scoring unit tests."""
    return Finding(
        source=source,
        tool=tool,
        category=category,
        title=title,
        severity=severity,
        confidence=confidence,
        description="d",
        affected_url=affected_url,
        endpoint=endpoint,
        param=param,
        impact="i",
        remediation="r",
    )
