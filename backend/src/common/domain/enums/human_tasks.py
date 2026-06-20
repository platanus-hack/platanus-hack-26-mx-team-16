"""Enums for the unified ``HumanTask`` (F6).

One entity replaces the previously-separate clarification + review notions: a
durable pause where a human (or an external system) supplies data or an approval
before the pipeline resumes.
"""

from src.common.domain.enums.base_enum import BaseEnum


class HumanTaskKind(BaseEnum):
    CLARIFICATION = "clarification"  # ask a human/system for missing data
    APPROVAL = "approval"  # ask a human to approve/reject
    # E6 · QA sampling: auditoría fire-and-forget post-COMPLETED sobre casos
    # auto-aprobados. No pausa Temporal (el run ya terminó) — solo registra
    # qa.passed/qa.failed en case_events.
    QA = "qa"


class HumanTaskStatus(BaseEnum):
    PENDING = "pending"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

    @property
    def is_open(self) -> bool:
        return self == self.PENDING


class HumanTaskAssigneeMode(BaseEnum):
    INTERNAL_QUEUE = "internal_queue"  # a Doxiq-hosted review queue picks it up
    EXTERNAL_CALLBACK = "external_callback"  # an external system resolves via API
