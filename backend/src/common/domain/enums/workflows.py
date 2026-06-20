from src.common.domain.enums.base_enum import BaseEnum

# E7 · F2: `WorkflowType` (STANDARD|ANALYSIS) retirado — un solo tipo de workflow
# cuyas capacidades deriva su pipeline (derive_capabilities).


class WorkflowDocumentSource(str, BaseEnum):
    """Provenance of a WorkflowDocument row.

    SINGLE: created by the per-card drop-zone flow; document_type_id is pre-assigned
    and re-extraction updates the same row in place.

    BULK: created by the global upload-and-extract flow from a multi-document file;
    may have siblings sharing the same file; re-extraction deletes all siblings
    and re-creates them from a fresh Temporal run.
    """

    SINGLE = "SINGLE"
    BULK = "BULK"
    # E3 · documentos virtuales (plan §4.1.3): "todo dato es un documento".
    # EXTERNAL_DATA: payload validado inyectado por el cliente (POST /v1/cases/{id}/data).
    # TOOL: resultado de una tool de la fase enrich (@slug disponible para reglas/output).
    EXTERNAL_DATA = "EXTERNAL_DATA"
    TOOL = "TOOL"
    # E5 · fan-out a child cases (Caso 3): doc clasificado repartido a su
    # child case por classify_pages con fan_out=child_cases;
    # `parent_document_id` apunta al doc bulk original si existe.
    SPLIT_CHILD = "SPLIT_CHILD"


class WorkflowDocumentStatus(str, BaseEnum):
    """Lifecycle states of a WorkflowDocument."""

    EMPTY = "EMPTY"
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    ERROR = "ERROR"


class WorkflowProcessingJobStatus(BaseEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"

    @property
    def is_active(self) -> bool:
        """In-flight: claimed by a worker or currently driving the pipeline."""
        return self in (
            WorkflowProcessingJobStatus.RUNNING,
            WorkflowProcessingJobStatus.PROCESSING,
        )

    @property
    def is_terminal_success(self) -> bool:
        """Pipeline finished with at least one document persisted."""
        return self in (
            WorkflowProcessingJobStatus.COMPLETED,
            WorkflowProcessingJobStatus.PARTIAL,
        )

    @property
    def is_failed(self) -> bool:
        return self is WorkflowProcessingJobStatus.FAILED

    @property
    def is_terminal(self) -> bool:
        return self.is_terminal_success or self.is_failed

    @property
    def is_idempotent_skip(self) -> bool:
        """The dispatcher must NOT restart Temporal when the set is already
        in one of these states (active or terminal-success). FAILED is the
        only state where a re-dispatch is allowed implicitly."""
        return self.is_active or self.is_terminal_success


class WorkflowProcessingJobTrigger(str, BaseEnum):
    """Origin of a processing-job dispatch."""

    USER = "USER"
    RETRY = "RETRY"
    ORPHAN_SWEEPER = "ORPHAN_SWEEPER"
    SYSTEM = "SYSTEM"


# Analysis-run enums moved to src.common.domain.enums.workflow_rules
# (WorkflowAnalysisRunStatus, WorkflowAnalysisRunTrigger).
