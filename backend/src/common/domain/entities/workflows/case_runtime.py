"""I/O de las activities del motor de caso E4 (await_documents · gate · review).

Viven en ``common/domain/entities/workflows`` para que el código de workflow
las importe dentro de ``workflow.unsafe.imports_passed_through()`` sin arrastrar
SQLAlchemy al sandbox determinista.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ─── resolve_classifier (F3 · D-C) ───────────────────────────────────────────


class ResolveClassifierInput(BaseModel):
    tenant_id: UUID
    slug: str

    model_config = ConfigDict(extra="forbid")


class ResolveClassifierOutput(BaseModel):
    """Contrato resuelto de un classifier del registry (kind lambda|prompt|tool).

    ``found=False`` ⇒ slug inexistente/deshabilitado: ``classify_pages`` cae al
    lambda base (degradación segura, no rompe el run)."""

    found: bool = False
    kind: str | None = None
    lambda_function: str | None = None
    lambda_alias: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


# ─── await_documents ─────────────────────────────────────────────────────────


class EvaluateCaseCompletenessInput(BaseModel):
    tenant_id: UUID
    case_id: UUID

    model_config = ConfigDict(extra="forbid")


class EvaluateCaseCompletenessOutput(BaseModel):
    """Snapshot de completitud — shape estable (se persiste tal cual en
    ``workflow_cases.completeness`` y lo lee el FE)."""

    satisfied: bool
    auto_ready: bool = False
    required: dict[str, int] = Field(default_factory=dict)
    present: dict[str, int] = Field(default_factory=dict)
    # [{"documentType": slug, "missing": n}]
    missing: list[dict[str, Any]] = Field(default_factory=list)
    changed: bool = False
    # E5 · fan-out: un child case (parent_case_id != NULL) nace completo —
    # ``await_documents`` lo auto-readea al primer ``case_docs_changed``.
    is_child: bool = False

    model_config = ConfigDict(extra="forbid")


class MarkCaseReadyInput(BaseModel):
    tenant_id: UUID
    case_id: UUID
    forced: bool = False
    auto: bool = False

    model_config = ConfigDict(extra="forbid")


class MarkCaseReadyOutput(BaseModel):
    ready_at: str | None = None  # ISO; None solo si el caso desapareció
    transitioned: bool = False  # RECEIVING→PROCESSING aplicada en esta llamada

    model_config = ConfigDict(extra="forbid")


# ─── case_events (timeline) ──────────────────────────────────────────────────


class AppendCaseEventInput(BaseModel):
    tenant_id: UUID
    case_id: UUID
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    actor: str | None = None
    # Idempotencia ante retries de la activity: mismo dedupe_key ⇒ una fila.
    dedupe_key: str | None = None

    model_config = ConfigDict(extra="forbid")


# ─── QA sampling post-COMPLETED (E6 · §3) ────────────────────────────────────


class OpenQaAuditTaskInput(BaseModel):
    """Abre (idempotente) la HumanTask de auditoría QA tras COMPLETED.

    Fire-and-forget: la task NO pausa el run (``pipeline_run_id`` vacío) — el
    run ya terminó. La activity sólo crea la task si el caso fue AUTO-aprobado
    (existe ``review.skipped`` y NO un ``review.approved`` humano); ``run_id`` es
    el último run de análisis (para el bench QA). El muestreo determinista ya se
    decidió en el workflow (clave = case_id)."""

    task_key: str
    tenant_id: UUID
    workflow_id: UUID
    case_id: UUID
    run_id: str | None = None
    audience: str | None = "doxiq_analyst"

    model_config = ConfigDict(extra="forbid")


class OpenQaAuditTaskOutput(BaseModel):
    # None ⇒ no se creó (el caso no era auto-aprobado): el hook es no-op.
    task_id: UUID | None = None
    created: bool = False

    model_config = ConfigDict(extra="forbid")


# ─── confidence_gate (ActivationPolicy) ──────────────────────────────────────


class EvaluateActivationGateInput(BaseModel):
    tenant_id: UUID
    case_id: UUID
    # ActivationPolicy sellada con la versión (dict crudo del scratch).
    activation_policy: dict[str, Any]

    model_config = ConfigDict(extra="forbid")


class EvaluateActivationGateOutput(BaseModel):
    # Items camelCase {documentId, documentType, fieldPath, confidence,
    # threshold, parseConfidence, extractConfidence, signals, candidates,
    # page, bbox} — compactos (límite 2 MiB de Temporal).
    items: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


# ─── pausas con contexto rico ────────────────────────────────────────────────


class OpenClarificationTaskInput(BaseModel):
    task_key: str
    tenant_id: UUID
    workflow_id: UUID
    case_id: UUID
    pipeline_run_id: str
    items: list[dict[str, Any]] = Field(default_factory=list)  # gate items
    expires_in_hours: float | None = None
    audience: str | None = None

    model_config = ConfigDict(extra="forbid")


class OpenApprovalTaskInput(BaseModel):
    task_key: str
    tenant_id: UUID
    workflow_id: UUID
    case_id: UUID
    pipeline_run_id: str
    # "approval" ⇒ payload {caseId, verdict, summary, signals} del último run;
    # "gate_review" ⇒ payload {caseId, items} (los gate items).
    trigger: str = "approval"
    gate_items: list[dict[str, Any]] | None = None
    audience: str | None = None
    # E5 · §3.1: "review_l1" | "review_l2"; None = gate único E4.
    stage: str | None = None
    # F4 · quórum: se sella en el payload de la task para que el endpoint de
    # resolución acumule votos hasta N. Default (1) ⇒ gate single (compat).
    approvals_required: int = 1
    distinct_approvers: bool = True
    approver_users: list[str] = Field(default_factory=list)
    approver_roles: list[str] = Field(default_factory=list)
    approver_audience: str | None = None

    model_config = ConfigDict(extra="forbid")


class OpenCaseTaskOutput(BaseModel):
    task_id: UUID
    # El payload persistido en la HumanTask (clarification request §4.5 o el
    # contexto de aprobación) — el webhook lo reusa tal cual.
    payload: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


# ─── human_review multinivel (E5 · §3.1) ─────────────────────────────────────


class BuildStageGateItemsInput(BaseModel):
    """Gate items frescos para un stage de revisión: relee los docs del caso
    en el momento del stage (activity — jamás payload de señal). El filtro
    Rossum del L2 excluye fieldPaths con ``verification.level >= 1``."""

    tenant_id: UUID
    case_id: UUID
    # ActivationPolicy sellada con la versión (dict crudo del scratch).
    activation_policy: dict[str, Any]
    # Excluir items cuyo fieldPath ya tenga verification.level >= este valor.
    # None ⇒ sin filtro (stage L1).
    exclude_verified_level: int | None = None

    model_config = ConfigDict(extra="forbid")


class BuildStageGateItemsOutput(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


# ─── human_review by_exception ───────────────────────────────────────────────


class CheckBlockingResultsInput(BaseModel):
    tenant_id: UUID
    case_id: UUID
    severities: list[str] = Field(default_factory=lambda: ["BLOCKER"])

    model_config = ConfigDict(extra="forbid")


class CheckBlockingResultsOutput(BaseModel):
    blocking: bool = False

    model_config = ConfigDict(extra="forbid")


# ─── fan-out a child cases (E5 · diseño §2) ──────────────────────────────────


class ChildCaseDocumentRef(BaseModel):
    """Ref compacto de un doc clasificado que parirá un child case."""

    document_id: UUID
    document_index: int
    document_type_name: str | None = None

    model_config = ConfigDict(extra="forbid")


class CreateChildCasesInput(BaseModel):
    tenant_id: UUID
    workflow_id: UUID
    parent_case_id: UUID
    documents: list[ChildCaseDocumentRef]
    # E5 · fan-out (C2): discrimina la clave determinista del child por origen —
    # un 2º archivo al mismo padre crea HERMANOS nuevos (con su webhook
    # ``case.created``) en vez de absorber children ajenos ya COMPLETED. El
    # ``file_id`` es estable dentro del run ⇒ la idempotencia de retries se
    # conserva. ``processing_job_uuid`` es el fallback cuando no hay file_id.
    file_id: UUID | None = None
    processing_job_uuid: UUID | None = None

    model_config = ConfigDict(extra="forbid")


class ChildCaseRef(BaseModel):
    """Ref compacto de retorno (límite 2 MiB: jamás el caso entero)."""

    case_id: UUID
    document_index: int
    external_ref: str | None = None

    model_config = ConfigDict(extra="forbid")


class CreateChildCasesOutput(BaseModel):
    children: list[ChildCaseRef]
    created: int = 0

    model_config = ConfigDict(extra="forbid")


class StartChildCaseRunsInput(BaseModel):
    """Batch (≤20 por activity) de children a arrancar/señalar desde finalize."""

    tenant_id: UUID
    case_ids: list[UUID]

    model_config = ConfigDict(extra="forbid")


class StartChildCaseRunsOutput(BaseModel):
    started: int = 0
    signaled: int = 0

    model_config = ConfigDict(extra="forbid")


# ─── señal al CASE# workflow desde otras activities ──────────────────────────


class SignalCaseWorkflowInput(BaseModel):
    case_id: UUID
    signal: str = "case_docs_changed"
    payload: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")
