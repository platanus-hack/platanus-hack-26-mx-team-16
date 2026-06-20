"""Enums for the workflow cases domain.

E4 (Expediente formal): la máquina de estados pública del caso pasa de
``DRAFT | IN_PROGRESS | COMPLETED | ARCHIVED`` a los 11 estados del diseño
(E4; ver ``product/plans/re-architecture/re-architecture.md``). ``REVIEW_L1``/``REVIEW_L2`` se declaran pero solo
se alcanzan en E5. Las transiciones legales viven en
``src.workflows.domain.services.case_state_machine``.
"""

from src.common.domain.enums.base_enum import BaseEnum


class WorkflowCaseStatus(str, BaseEnum):
    RECEIVING = "RECEIVING"
    PROCESSING = "PROCESSING"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    ANALYZING = "ANALYZING"
    REVIEW_L1 = "REVIEW_L1"
    REVIEW_L2 = "REVIEW_L2"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"

    @property
    def is_receiving(self) -> bool:
        return self == WorkflowCaseStatus.RECEIVING

    @property
    def is_processing(self) -> bool:
        return self == WorkflowCaseStatus.PROCESSING

    @property
    def is_completed(self) -> bool:
        return self == WorkflowCaseStatus.COMPLETED

    @property
    def is_archived(self) -> bool:
        return self == WorkflowCaseStatus.ARCHIVED

    @property
    def is_terminal(self) -> bool:
        """ARCHIVED es el único estado sin transiciones salientes."""
        return self == WorkflowCaseStatus.ARCHIVED
