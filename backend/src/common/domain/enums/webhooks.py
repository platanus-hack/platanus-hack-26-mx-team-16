from src.common.domain.enums.base_enum import BaseEnum


class PaymentWebhookEventStatus(BaseEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @property
    def is_pending(self) -> bool:
        return self == self.PENDING

    @property
    def is_processing(self) -> bool:
        return self == self.PROCESSING

    @property
    def is_completed(self) -> bool:
        return self == self.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self == self.FAILED


class WebhookEventType(BaseEnum):
    """Outbound webhook event types (spec §4.1.1 · W1, ampliada en E2).

    STANDARD extraction emits ``document.*``. ANALYSIS: los runs manuales
    conservan ``analysis_run.completed`` (W1); las recetas encadenadas E2
    (fase ``deliver``) emiten además los checkpoints del caso ``case.*``
    (plan re-architecture §4.4 — supersede el "no per-case events" de W1).
    Los destinos se suscriben explícitamente (opt-in, sin cambio de defaults)."""

    DOCUMENT_EXTRACTED = "document.extracted"  # WorkflowDocument.status == EXTRACTED
    DOCUMENT_FAILED = "document.failed"  # WorkflowDocument.status == ERROR
    ANALYSIS_RUN_COMPLETED = "analysis_run.completed"  # WorkflowAnalysisRun finalised (W1)
    CASE_CREATED = "case.created"  # caso creado vía API M2M (E3, solo en creación real)
    CASE_OUTPUT_READY = "case.output.ready"  # fase deliver: output del caso listo (E2)
    CASE_FAILED = "case.failed"  # fase analyze/output falló de forma terminal (E2)
    CASE_NEEDS_REVIEW = "case.needs_review"  # gate review / approval pausó el caso (E4)
    CASE_NEEDS_CLARIFICATION = "case.needs_clarification"  # clarification request §4.5 (E4)
    CASE_REVIEW_COMPLETED = "case.review.completed"  # último stage L1/L2 cerrado (E5 §3.1)
    REVIEW_PENDING = "review.pending"  # a human_review HumanTask awaits action (F6)
    NEEDS_CLARIFICATION = "needs_clarification"  # an await_clarification HumanTask opened (F6)
    DOCUMENT_RECEIVED = "document.received"  # a Source ingested a file (F12 · Slack §2a)


class WorkflowEventDeliveryStatus(BaseEnum):
    """Delivery state of a persisted ``WorkflowEvent`` (spec §4.1.1)."""

    PENDING = "PENDING"  # created, not delivered yet
    DELIVERING = "DELIVERING"  # attempt in progress
    DELIVERED = "DELIVERED"  # 2xx from receiver
    FAILED = "FAILED"  # retries exhausted / definitive 4xx
    SKIPPED = "SKIPPED"  # created but not delivered: event type not subscribed (gate ON)

    @property
    def is_pending(self) -> bool:
        return self == self.PENDING

    @property
    def is_delivering(self) -> bool:
        return self == self.DELIVERING

    @property
    def is_delivered(self) -> bool:
        return self == self.DELIVERED

    @property
    def is_failed(self) -> bool:
        return self == self.FAILED

    @property
    def is_skipped(self) -> bool:
        return self == self.SKIPPED
