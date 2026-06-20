"""Pipeline interpreter runtime (F1 · decision A1 · generalizado en E1).

The interpreter is a single generic loop: for each :class:`PhaseSpec` in the
sealed recipe, look up its handler in :data:`PHASE_LIBRARY` and ``await`` it
with the workflow context and the threaded :class:`PipelineState`. Adding a
capability (enrich, confidence_gate, human_review …) means registering a
handler — never editing the loop. This module runs *inside* the Temporal workflow sandbox, so it only touches
``workflow.execute_activity`` (via the ctx helpers) and deterministic data.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from temporalio import workflow
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    from src.common.domain.entities.workflows.document_processing import (
        DocumentProcessingInput,
        DocumentProcessingOutput,
    )
    from src.workflows.domain.models.pipeline import PhaseSpec
    from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
        ClassifiedDocumentRef,
        PersistedDocumentRef,
    )


@dataclass
class PipelineState:
    """Mutable run state threaded through every phase — *the data a pipeline is*.

    ``artifacts`` is a generic per-phase map (E1): each phase records its output
    under a stable key. **Contract**: artifacts hold S3 refs + compact metadata
    only — never payloads that can grow past Temporal's 2 MiB history limit
    (TMPRL1103); large data stays in S3 and travels as ``output_uri`` refs.

    The extraction family keeps typed accessors (properties below) so its
    handlers stay readable and cross-phase references (`classify_pages` reads
    the `extract_text` ref) have one obvious spelling. New phase families write
    their own keys via :meth:`artifact` / :meth:`put_artifact` instead of
    bolting fields onto this class.
    """

    data: DocumentProcessingInput
    job_id: str

    # phase key → artifact (S3 refs + compact metadata only; see class docstring)
    artifacts: dict[str, Any] = field(default_factory=dict)

    # generic scratch for cross-phase signals (gate, resolutions, policies…)
    scratch: dict[str, Any] = field(default_factory=dict)

    # short-circuit: a phase may end the run early (e.g. no documents to extract)
    terminated: bool = False
    output: DocumentProcessingOutput | None = None

    # -- generic artifact access ------------------------------------------------
    def artifact(self, key: str, default: Any = None) -> Any:
        return self.artifacts.get(key, default)

    def put_artifact(self, key: str, value: Any) -> None:
        self.artifacts[key] = value

    # -- typed accessors for the extraction family ------------------------------
    @property
    def extract_text(self) -> dict:
        return self.artifacts.get("extract_text") or {}

    @extract_text.setter
    def extract_text(self, value: dict) -> None:
        self.artifacts["extract_text"] = value

    @property
    def classify_pages(self) -> dict:
        return self.artifacts.get("classify_pages") or {}

    @classify_pages.setter
    def classify_pages(self, value: dict) -> None:
        self.artifacts["classify_pages"] = value

    @property
    def documents(self) -> list[ClassifiedDocumentRef]:
        return self.artifacts.get("classified_documents") or []

    @documents.setter
    def documents(self, value: list[ClassifiedDocumentRef]) -> None:
        self.artifacts["classified_documents"] = value

    @property
    def persisted_docs(self) -> list[PersistedDocumentRef]:
        return self.artifacts.get("persisted_docs") or []

    @persisted_docs.setter
    def persisted_docs(self, value: list[PersistedDocumentRef]) -> None:
        self.artifacts["persisted_docs"] = value

    @property
    def survivors(self) -> list[PersistedDocumentRef]:
        return self.artifacts.get("survivors") or []

    @survivors.setter
    def survivors(self, value: list[PersistedDocumentRef]) -> None:
        self.artifacts["survivors"] = value

    @property
    def completed(self) -> list[PersistedDocumentRef]:
        return self.artifacts.get("completed") or []

    @completed.setter
    def completed(self, value: list[PersistedDocumentRef]) -> None:
        self.artifacts["completed"] = value

    @property
    def extract_fields(self) -> dict:
        return self.artifacts.get("extract_fields") or {}

    @extract_fields.setter
    def extract_fields(self, value: dict) -> None:
        self.artifacts["extract_fields"] = value

    @property
    def validate_extraction(self) -> dict:
        return self.artifacts.get("validate_extraction") or {}

    @validate_extraction.setter
    def validate_extraction(self, value: dict) -> None:
        self.artifacts["validate_extraction"] = value


class PhaseContext(Protocol):
    """What a handler needs from the interpreter workflow instance (the ctx).

    Implemented by :class:`ProcessingJobWorkflowBase` — the checkpoint/lambda/
    failure plumbing shared with the live extraction workflow.
    """

    async def _checkpoint(self, data: Any, **kwargs: Any) -> None: ...
    async def _invoke_lambda(self, function_name: str, payload: dict, timeout: Any, label: str) -> dict: ...
    async def _fail_document(self, data: Any, doc: Any, source_step: Any, err: dict) -> None: ...
    async def _fail_job(self, data: Any, source_step: Any, exc: Exception) -> None: ...


PhaseHandler = Callable[[PhaseContext, PhaseSpec, PipelineState], Awaitable[None]]

# id (PhaseKind value) → handler. Populated by the phase modules at import time.
PHASE_LIBRARY: dict[str, PhaseHandler] = {}

# id (PhaseKind value) → "document" | "case" (E4 · diseño §3). El intérprete
# filtra la receta por scope cuando ``PipelineRunInput.scope`` no es None; la
# validación de publicación exige document-scope antes de la primera case-scope.
PHASE_SCOPES: dict[str, str] = {}


def register_phase(kind: str, scope: str = "document") -> Callable[[PhaseHandler], PhaseHandler]:
    def _decorator(handler: PhaseHandler) -> PhaseHandler:
        PHASE_LIBRARY[kind] = handler
        PHASE_SCOPES[kind] = scope
        return handler

    return _decorator


def filter_phases_by_scope(phases: list[PhaseSpec], scope: str | None) -> list[PhaseSpec]:
    """``scope=None`` ⇒ receta completa (E1–E3 intactos). Si no, solo las fases
    cuyo scope registrado coincide (kind sin registro asume "document")."""
    if scope is None:
        return phases
    return [
        phase
        for phase in phases
        if PHASE_SCOPES.get(phase.kind.value if hasattr(phase.kind, "value") else str(phase.kind), "document")
        == scope
    ]


# Optional per-phase observer (feature "Ejecuciones"). The interpreter run calls
# it as ("STARTED"|"COMPLETED"|"FAILED", index, phase, state, started_at, error).
# Default None ⇒ NO extra activity calls, so every test/golden path that calls
# ``execute_pipeline`` directly keeps the exact legacy activity sequence.
PhaseObserver = Callable[[str, int, "PhaseSpec", "PipelineState", Any, "dict | None"], Awaitable[None]]


async def execute_pipeline(
    ctx: PhaseContext,
    phases: list[PhaseSpec],
    state: PipelineState,
    on_phase: PhaseObserver | None = None,
) -> PipelineState:
    """The interpreter loop. Deterministic over the sealed ``phases`` list.

    ``on_phase`` (passed only by ``PipelineInterpreterWorkflow.run``) records the
    per-phase execution timeline. It defaults to ``None`` so the legacy-parity
    golden — which calls ``execute_pipeline`` directly — sees an identical
    activity sequence; the recording is invisible to it.
    """
    for index, phase in enumerate(phases):
        if state.terminated:
            break
        handler = PHASE_LIBRARY.get(phase.kind.value)
        if handler is None:
            raise ApplicationError(
                f"No handler registered for phase kind '{phase.kind}'",
                type="pipeline.unknown_phase_kind",
                non_retryable=True,
            )
        started_at = workflow.now() if on_phase is not None else None
        if on_phase is not None:
            await on_phase("STARTED", index, phase, state, started_at, None)
        try:
            await handler(ctx, phase, state)
        except Exception as exc:  # noqa: BLE001 — recorded then re-raised unchanged
            if on_phase is not None:
                await on_phase(
                    "FAILED",
                    index,
                    phase,
                    state,
                    started_at,
                    {"type": type(exc).__name__, "message": str(exc)},
                )
            raise
        if on_phase is not None:
            await on_phase("COMPLETED", index, phase, state, started_at, None)
    return state


def _jsonable(value: Any) -> Any:
    """Recursively coerce artifacts (pydantic refs, lists, dicts) to JSON types."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    return value


def phase_output_snapshot(phase: PhaseSpec, state: PipelineState, limit: int = 16384) -> dict | None:
    """Compact JSON of the artifact a phase wrote, bounded for Temporal history.

    Artifacts hold S3 refs + metadata only (PipelineState contract), so this is
    small; the size cap is a backstop against an unexpectedly large dict.
    """
    key = phase.kind.value if hasattr(phase.kind, "value") else str(phase.kind)
    raw = state.artifacts.get(key)
    if raw is None:
        return None
    value = _jsonable(raw)
    encoded = json.dumps(value, default=str)
    if len(encoded) > limit:
        return {"truncated": True, "bytes": len(encoded)}
    return {"key": key, "value": value}
