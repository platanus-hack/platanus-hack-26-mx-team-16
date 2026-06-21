"""Redacted alert-content rendering (08-ranking-watchlists §5.3).

The alert identifies the **hostname**, the **previous → new grade**, and a list
of new ``critical`` findings (type/category/severity/short impact). It **never**
includes the raw exploitation payload — same redaction principle as the public
report ``/r/[token]``: an alert channel is not a place to leak real exploits
against the user's own site. ``build_alert_payload`` drops ``evidence`` and any
raw request/response entirely.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.scans.domain.models.finding import FindingRecord


@dataclass(slots=True)
class RedactedCritical:
    """A new critical finding, stripped to safe display fields only."""

    title: str
    category: str
    severity: str
    impact: str

    @property
    def to_dict(self) -> dict[str, str]:
        return {
            "title": self.title,
            "category": self.category,
            "severity": self.severity,
            "impact": self.impact,
        }


@dataclass(slots=True)
class AlertPayload:
    """The fully-redacted alert content, channel-agnostic."""

    hostname: str
    previous_grade: str | None
    current_grade: str | None
    grade_dropped: bool
    new_criticals: list[RedactedCritical] = field(default_factory=list)

    @property
    def subject(self) -> str:
        return f"Owliver alert: {self.hostname}"

    @property
    def summary_line(self) -> str:
        parts: list[str] = []
        if self.grade_dropped:
            prev = self.previous_grade or "?"
            curr = self.current_grade or "?"
            parts.append(f"grade dropped {prev} → {curr}")
        if self.new_criticals:
            parts.append(f"{len(self.new_criticals)} new critical finding(s)")
        return "; ".join(parts) or "monitoring update"

    def as_text(self) -> str:
        """Plain-text body (used for Slack ``text`` and the email context)."""
        lines = [f"Owliver detected a change on {self.hostname}: {self.summary_line}."]
        for crit in self.new_criticals:
            lines.append(
                f"  • [{crit.severity}] {crit.title} ({crit.category}) — {crit.impact}"
            )
        return "\n".join(lines)

    @property
    def to_dict(self) -> dict:
        return {
            "hostname": self.hostname,
            "previous_grade": self.previous_grade,
            "current_grade": self.current_grade,
            "grade_dropped": self.grade_dropped,
            "new_criticals": [c.to_dict for c in self.new_criticals],
            "summary_line": self.summary_line,
        }


def build_alert_payload(
    *,
    hostname: str,
    previous_grade: str | None,
    current_grade: str | None,
    grade_dropped: bool,
    new_criticals: list[FindingRecord],
) -> AlertPayload:
    """Build the redacted alert payload from raw findings.

    Only safe fields survive: ``title``, ``category``, ``severity`` and a short
    ``impact``. The raw ``evidence`` dict (which can carry real exploit
    request/response payloads) is never copied.
    """
    redacted = [
        RedactedCritical(
            title=finding.title,
            category=finding.category,
            severity=finding.severity,
            impact=finding.impact,
        )
        for finding in new_criticals
    ]
    return AlertPayload(
        hostname=hostname,
        previous_grade=previous_grade,
        current_grade=current_grade,
        grade_dropped=grade_dropped,
        new_criticals=redacted,
    )
