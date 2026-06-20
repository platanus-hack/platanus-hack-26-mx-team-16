"""Enums for the configurable pipeline engine (F1 · decision A1).

A *pipeline* is a versioned, immutable, ordered list of *phases* executed by a
single generic interpreter (``PipelineInterpreterWorkflow``). The phase ``kind``
selects a handler from ``PHASE_LIBRARY``; the phase ``config`` parameterises it.
"""

from enum import StrEnum


class PipelineKind(StrEnum):
    """What a pipeline produces end-to-end."""

    EXTRACTION = "EXTRACTION"  # OCR → classify → extract → validate (STANDARD)
    ANALYSIS = "ANALYSIS"  # rule evaluation + synthesis over a case


class PipelineStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class PhaseKind(StrEnum):
    """Library of phase handlers. One handler per kind in ``PHASE_LIBRARY``.

    The first wave (F2) mirrors the existing extraction lambdas one-to-one so the
    interpreter is a behavioural replica of ``run_extraction_pipeline``. Later
    phases (``enrich``, ``extraction_gate``, ``human_review`` …) are added by
    F4–F7 without touching the interpreter.
    """

    # ── extraction (F2) ────────────────────────────────────────────────
    INGEST = "ingest"  # seal input, DISPATCHED checkpoint
    EXTRACT_TEXT = "extract_text"  # OCR lambda
    CLASSIFY_PAGES = "classify_pages"  # split + classify lambda (+ persist refs)
    EXTRACT_FIELDS = "extract_fields"  # per-doc field extraction lambda
    ASSESS = "assess"  # capa-2 de confianza: LLM puntúa campos vs evidencia (E3)
    VALIDATE_EXTRACTION = "validate_extraction"  # per-doc validation lambda
    FINALIZE = "finalize"  # persist texts, mark docs, terminal + webhooks

    # ── enrichment / gating (F4·F5) ────────────────────────────────────
    EXTRACTION_GATE = "extraction_gate"  # gate pre-analyze consolidado (eval + clarify|review)
    ENRICH = "enrich"

    # ── analysis / output / delivery (E2 · plan §4.2) ──────────────────
    ANALYZE = "analyze"  # child WorkflowAnalysisRunWorkflow (D3) y espera
    OUTPUT = "output"  # proyección x-source + síntesis LLM vs output_schema
    DELIVER = "deliver"  # eventos case.output.ready/case.failed al outbox

    # ── durable human/data pauses (F6) ─────────────────────────────────
    AWAIT_CLARIFICATION = "await_clarification"
    HUMAN_REVIEW = "human_review"
    AWAIT_DOCUMENTS = "await_documents"


class ClassifierKind(StrEnum):
    """Motor de un clasificador del registry tenant-scoped (phases-config · F3).

    ``classify_pages.classifier`` referencia una entrada por slug; la resolución
    real (qué lambda/prompt/tool corre) ocurre en la activity ``resolve_classifier``
    para preservar el determinismo del workflow.
    """

    LAMBDA = "lambda"  # config: {function, alias?}
    PROMPT = "prompt"  # config: {provider, prompt_template, output_schema}
    TOOL = "tool"  # config: {tool_slug, transport}


class PhaseExecutionStatus(StrEnum):
    """Lifecycle of a single recipe phase inside an interpreter run (Ejecuciones)."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

    @property
    def is_terminal(self) -> bool:
        return self in (
            PhaseExecutionStatus.COMPLETED,
            PhaseExecutionStatus.FAILED,
            PhaseExecutionStatus.SKIPPED,
        )


class PhaseExecutionEvent(StrEnum):
    """Boundary the interpreter reports per phase via ``execute_pipeline``'s hook."""

    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
