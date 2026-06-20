"""Pydantic payloads for the WorkflowAnalysisRunWorkflow and its activities.

Kept under `common/domain/entities/workflows` so workflow code can import
them inside `workflow.unsafe.imports_passed_through()` without dragging
SQLAlchemy into the deterministic sandbox.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.common.domain.enums.workflow_rules import WorkflowAnalysisRunStatus


class AnalysisProviders(BaseModel):
    """phases-config · analyze.*_provider: overrides LLM por rol del run de análisis.
    Todos None (default) ⇒ env ``ANALYSIS_*_PROVIDER`` (comportamiento de hoy)."""

    parser: str | None = None
    reviewer: str | None = None  # rol "evaluator"
    critic: str | None = None  # rol declarado pero inerte hoy (sin call site)
    synthesizer: str | None = None  # narrativa del run (complete_analysis_run)

    model_config = ConfigDict(extra="forbid")


class AnalysisRunWorkflowInput(BaseModel):
    """Input to the WorkflowAnalysisRunWorkflow.

    Driven entirely from `run_id`; the load activity reloads the rest from
    the DB so the workflow always sees fresh state.
    """

    run_id: UUID
    workflow_id: UUID
    case_id: UUID
    tenant_id: UUID
    # phases-config · analyze: overrides de provider + rule_set, sellados en la
    # config de la fase analyze. Defaults ⇒ comportamiento de hoy (replay-safe).
    providers: AnalysisProviders = AnalysisProviders()
    rule_set: str | None = None

    model_config = ConfigDict(extra="forbid")


class CombinationPayload(BaseModel):
    """One concrete invocation of a rule against a combination."""

    rule_id: UUID
    combination_index: int
    document_refs: dict[str, Any]
    document_refs_hash: str
    document_ids: list[UUID]
    is_synthetic_empty: bool = False
    synthetic_outcome: str | None = None

    model_config = ConfigDict(extra="forbid")


class AnalysisRunPlan(BaseModel):
    """Output of `load_analysis_run_plan`. Workflow fans out over `evaluations`."""

    run_id: UUID
    workflow_id: UUID
    case_id: UUID
    tenant_id: UUID
    case_name: str | None
    evaluations: list[CombinationPayload]
    providers: AnalysisProviders = AnalysisProviders()

    model_config = ConfigDict(extra="forbid")


class EvaluateCombinationInput(BaseModel):
    run_id: UUID
    workflow_id: UUID
    case_id: UUID
    tenant_id: UUID
    case_name: str | None
    combination: CombinationPayload
    providers: AnalysisProviders = AnalysisProviders()

    model_config = ConfigDict(extra="forbid")


class EvaluateCombinationOutput(BaseModel):
    """What `evaluate_rule_combination` returns to the workflow.

    `result_payload` is the already-presented dict (camelCase) so the
    workflow can publish it verbatim as the `RULE_RESULT_READY` event
    payload without re-hitting the DB.
    """

    rule_id: UUID
    result_uuid: UUID
    status: str
    is_passed: bool | None
    has_error: bool
    error: str | None = None
    result_payload: dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class UpdateAnalysisRunStatusInput(BaseModel):
    run_id: UUID
    tenant_id: UUID
    status: WorkflowAnalysisRunStatus
    error: str | None = None
    completed: bool = False
    canceled_by: UUID | None = None
    rules_passed: int | None = None
    rules_failed: int | None = None
    rules_inconclusive: int | None = None

    model_config = ConfigDict(extra="forbid")


class CompleteAnalysisRunInput(BaseModel):
    run_id: UUID
    tenant_id: UUID
    providers: AnalysisProviders = AnalysisProviders()

    model_config = ConfigDict(extra="forbid")


# ─── E2 · fases analyze/output/deliver del intérprete ────────────────────────


class CreateAnalysisRunForPipelineInput(BaseModel):
    """Crea (idempotente por ``run_id`` determinista del workflow) la fila del
    run ANTES del child workflow. Si hay un run activo AJENO para el caso, la
    activity falla con error reintentable — el retry policy de la fase es la
    espera (los uploads concurrentes se serializan)."""

    run_id: UUID
    tenant_id: UUID
    workflow_id: UUID
    case_id: UUID

    model_config = ConfigDict(extra="forbid")


class CreateAnalysisRunForPipelineOutput(BaseModel):
    run_id: UUID
    created: bool

    model_config = ConfigDict(extra="forbid")


class MarkAnalysisRunFailedInput(BaseModel):
    run_id: UUID
    tenant_id: UUID
    error: str

    model_config = ConfigDict(extra="forbid")


class BuildCaseOutputInput(BaseModel):
    run_id: UUID
    tenant_id: UUID
    workflow_id: UUID
    case_id: UUID
    # phases-config · output.synthesizer_provider override; None ⇒ env.
    synthesizer_provider: str | None = None

    model_config = ConfigDict(extra="forbid")


class BuildCaseOutputOutput(BaseModel):
    """Resultado compacto de la fase output — refs/metadata, NUNCA el output
    inline (límite 2 MiB de Temporal; el output vive en el summary)."""

    run_id: UUID
    verdict: str | None = None
    narrative_status: str | None = None
    has_output: bool = False
    document_outputs: int = 0
    warnings: list[str] = []

    model_config = ConfigDict(extra="forbid")


class DispatchCaseEventInput(BaseModel):
    tenant_id: UUID
    workflow_id: UUID
    case_id: UUID
    event_type: str  # WebhookEventType: case.output.ready | case.failed | case.needs_*
    run_id: UUID | None = None
    error: dict[str, Any] | None = None  # solo case.failed
    # E4 · case.needs_review / case.needs_clarification: idempotencia por
    # ``case:{case_id}:task:{task_id}`` y payload rico de la pausa (el
    # clarification request §4.5 o el contexto de aprobación).
    task_id: UUID | None = None
    payload: dict[str, Any] | None = None
    # phases-config · deliver.channels: allowlist de destinos (uuid o name).
    # None ⇒ todos los enabled+suscritos (comportamiento de hoy).
    channels: list[str] | None = None
    # phases-config · deliver.payload_projection: subset de campos del `output`
    # en case.output.ready. None ⇒ envelope completo (hoy).
    payload_projection: list[str] | None = None

    model_config = ConfigDict(extra="forbid")
