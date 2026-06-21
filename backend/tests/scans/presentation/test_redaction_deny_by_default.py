"""Deny-by-default tests for the redaction boundary (09-reporting §4).

A field that is not in ``SAFE_FIELDS`` (and is not one of the few explicitly
projected identity/trend keys) must NOT appear in the public projection. This
guards against a future ``FindingRecord`` field silently leaking an exploit.
"""

from uuid import uuid4

from expects import equal, expect

from src.scans.domain.models.finding import FindingRecord
from src.scans.presentation.presenters.redaction import SAFE_FIELDS, redact_finding


def _finding() -> FindingRecord:
    return FindingRecord(
        uuid=uuid4(),
        scan_id=uuid4(),
        site_id=uuid4(),
        source="owasp",
        tool="sqlmap",
        category="A03",
        title="SQL injection",
        severity="high",
        confidence="alta",
        description="the raw description may contain the exploit narrative",
        evidence={"request": "' OR 1=1 --"},
        affected_url="https://victim.example/login",
        endpoint="/login",
        param="username",
        impact="i",
        remediation="r",
        references=[],
        status="open",
        dedupe_key=f"k-{uuid4()}",
    )


def test_param_and_description_are_not_in_public_projection():
    """``param`` (where to inject) and ``description`` (raw narrative) are not
    in SAFE_FIELDS, so they must not surface in the public dict."""
    keys = set(redact_finding(_finding(), public=True).keys())

    expect("param" in keys).to(equal(False))
    expect("description" in keys).to(equal(False))


def test_safe_fields_is_the_allowlist_and_excludes_evidence():
    expect("evidence" in SAFE_FIELDS).to(equal(False))
    # The deny-by-default allowlist is exactly the spec §5 "always shown" set.
    expect(set(SAFE_FIELDS)).to(
        equal(
            {
                "source",
                "category",
                "severity",
                "confidence",
                "impact",
                "remediation",
                "references",
                "title",
            }
        )
    )
