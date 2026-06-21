"""The exploit-redaction boundary for reports (09-reporting §4 / spec §5).

This is the **single, deterministic** place that decides which fields of a
``FindingRecord`` are projected into a report, and — critically — which field is
**hidden** in the public ``/r/{token}`` report.

Security rule (spec §5, non-recortable): a public share link must **never** leak
a reproducible exploit against the user's own site. Concretely, the only field
that crosses the redaction boundary is ``evidence`` (the prompt-injection
payload, the sqlmap request, the leaked system-prompt, replayable req/resp, and
the attack screenshots). Everything else —
``source/category/severity/confidence/impact/remediation/references/title`` — is
**always** visible (public and authenticated alike).

The projection is **deny-by-default**: only the names in :data:`SAFE_FIELDS`
(plus ``affectedUrl`` and the trend metadata) leave this function. If 06 adds a
new field to ``FindingRecord``, it does **not** surface in the public report
until someone consciously adds it to ``SAFE_FIELDS`` — a new sensitive field
cannot leak an exploit by accident.
"""

from __future__ import annotations

from typing import Any

from src.scans.domain.models.finding import FindingRecord

#: Fields ALWAYS shown — in both the public and authenticated reports (spec §5).
#: ``evidence`` is intentionally absent: it is the only field the public report
#: redacts, and it is added back explicitly (and only) for the authenticated view.
SAFE_FIELDS: tuple[str, ...] = (
    "source",
    "category",
    "severity",
    "confidence",
    "impact",
    "remediation",
    "references",
    "title",
)


def redact_finding(finding: FindingRecord, *, public: bool) -> dict[str, Any]:
    """Project a ``FindingRecord`` to a camelCase dict.

    When ``public`` is ``True`` the raw ``evidence`` (exploit payload, req/resp,
    leaked system-prompt, attack screenshots) is **omitted** and replaced with an
    ``evidenceRedacted: True`` flag so the UI can render an "evidence hidden"
    placeholder without ever shipping the exploit. When ``public`` is ``False``
    (the owner's authenticated report) the full ``evidence`` is included.

    The parameter is the **persisted** ``FindingRecord`` (not the frozen
    ``Finding`` contract): only the record exposes ``status``/``first_seen``/
    ``last_seen``, which the technical layer reads for the historical trend.
    """
    base: dict[str, Any] = {name: getattr(finding, name) for name in SAFE_FIELDS}

    # Identity + the site the finding is on. The owner already knows their own
    # site; for the public report the hostname is already public information, so
    # this never leaks an exploit. The reproducible payload lives only in
    # ``evidence`` (redacted below for the public report).
    base["findingId"] = str(finding.uuid)
    base["tool"] = finding.tool
    base["affectedUrl"] = finding.affected_url
    base["endpoint"] = finding.endpoint

    # Trend metadata (09 §3.2) — read from the persisted record, presented only.
    base["status"] = finding.status
    base["firstSeen"] = finding.first_seen
    base["lastSeen"] = finding.last_seen

    if public:
        # REDACTED — never ship a reproducible exploit through a public link.
        base["evidence"] = None
        base["evidenceRedacted"] = True
    else:
        base["evidence"] = finding.evidence
        base["evidenceRedacted"] = False

    return base
