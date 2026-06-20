"""Plano 2 de la API pública: el expediente (E3 · plan §4.4 · ampliado E4).

``POST /v1/cases`` (find-or-create por external_ref + evento case.created +
arranque del run CASE# si la receta espera documentos), ``POST
/v1/cases/{id}/data`` (documento virtual + señal/auto-start), ``GET
/v1/cases/{id}`` (estado compuesto + timeline + completeness + readyAt),
``GET /v1/cases/{id}/completeness`` (cálculo fresco), ``POST
/v1/cases/{id}/ready`` (idempotente; 409 ``case.not_complete`` con missing) y
``GET /v1/cases/{id}/output`` (output del último run COMPLETED).
Auth por API key ``dxk_`` (X-Api-Key), igual que el resto del plano M2M.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from src.common.application.logging import get_logger
from src.common.database.config import get_database_config
from src.common.domain.entities.workflows.analysis_run_processing import (
    DispatchCaseEventInput,
)
from src.common.domain.enums.webhooks import WebhookEventType
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import (
    AsyncSessionDep,
    DomainContextDep,
    TemporalClientDep,
)
from src.common.infrastructure.dependencies.tenant_api_key import get_tenant_from_api_key
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.settings import settings
from src.workflows.application.workflow_cases.case_run_starter import EnsureCaseRunStarted
from src.workflows.application.workflow_cases.completeness import EvaluateCaseCompleteness
from src.workflows.application.workflow_cases.m2m import (
    FindOrCreateCaseM2M,
    GetCaseM2M,
    GetCaseOutputM2M,
    SubmitCaseData,
)
from src.workflows.application.workflow_cases.ready import RequestCaseReady

logger = get_logger(__name__)


# ── Requests ────────────────────────────────────────────────────────────────
class CreateCaseRequest(BaseModel):
    workflow: UUID
    external_ref: str | None = Field(default=None, max_length=255)
    pipeline: str | None = Field(default=None, max_length=120)
    name: str | None = Field(default=None, max_length=255)


class SubmitCaseDataRequest(BaseModel):
    doc_type: str = Field(..., min_length=1, max_length=255)
    payload: dict = Field(default_factory=dict)
    auto_start: bool = True


class ReadyCaseRequest(BaseModel):
    force: bool = False


# ── Presenters ──────────────────────────────────────────────────────────────
def _present_case(case) -> dict:
    return {
        "case_id": str(case.uuid),
        "workflow_id": str(case.workflow_id),
        "name": case.name,
        "status": case.status.value if hasattr(case.status, "value") else case.status,
        "external_ref": case.external_ref,
        "pipeline_id": str(case.pipeline_id) if case.pipeline_id else None,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        # E5 · fan-out: lineage child→padre (null en casos normales).
        "parentCaseId": str(case.parent_case_id) if case.parent_case_id else None,
    }


def _present_timeline(events) -> list[dict]:
    # Shape exacto del FE (E4): [{uuid, type, payload, actor, createdAt}].
    return [
        {
            "uuid": str(e.uuid),
            "type": e.type,
            "payload": e.payload,
            "actor": e.actor,
            "createdAt": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events or []
    ]


def _present_completeness(result) -> dict:
    # Shape exacto del FE (E4): camelCase, missing = [{documentType, missing}].
    return {
        "satisfied": result.satisfied,
        "autoReady": result.auto_ready,
        "readyAt": result.case.ready_at.isoformat() if result.case.ready_at else None,
        "required": result.snapshot.get("required") or {},
        "present": result.snapshot.get("present") or {},
        "missing": result.snapshot.get("missing") or [],
    }


def _present_case_aggregate(aggregate) -> dict:
    payload = _present_case(aggregate.case)
    # E5 · fan-out: resumen de children {total, byStatus} — solo si es padre.
    children_by_status = getattr(aggregate, "children_by_status", None) or {}
    if children_by_status:
        payload["children"] = {
            "total": sum(children_by_status.values()),
            "byStatus": dict(children_by_status),
        }
    # E4: timeline + completitud + readyAt (camelCase — shapes del FE).
    payload["timeline"] = _present_timeline(aggregate.timeline)
    payload["completeness"] = aggregate.case.completeness
    payload["readyAt"] = (
        aggregate.case.ready_at.isoformat() if aggregate.case.ready_at else None
    )
    payload["documents"] = [
        {
            "document_id": str(d.uuid),
            "document_type_id": str(d.document_type_id) if d.document_type_id else None,
            "source": d.source.value if hasattr(d.source, "value") else d.source,
            "status": d.processing_status or (d.status.value if d.status else None),
            "file_name": d.file_name,
        }
        for d in aggregate.documents
    ]
    payload["runs"] = [
        {
            "run_id": str(r.uuid),
            "status": r.status.value if hasattr(r.status, "value") else r.status,
            "trigger": r.trigger.value if hasattr(r.trigger, "value") else r.trigger,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if getattr(r, "completed_at", None) else None,
        }
        for r in aggregate.runs
    ]
    summary = aggregate.latest_summary
    payload["latest_output"] = (
        {
            "verdict": summary.verdict.value if summary.verdict else None,
            "confidence_score": summary.confidence_score,
            "narrative_status": summary.narrative_status.value if summary.narrative_status else None,
            "has_output": summary.output is not None,
        }
        if summary is not None
        else None
    )
    return payload


# ── Endpoints ───────────────────────────────────────────────────────────────
async def create_case(
    request: CreateCaseRequest,
    session: AsyncSessionDep,
    domain: DomainContextDep,
    temporal_client: TemporalClientDep,
    tenant: Tenant = Depends(get_tenant_from_api_key),
) -> ApiJSONResponse:
    result = await FindOrCreateCaseM2M(
        tenant_id=tenant.uuid,
        workflow_id=request.workflow,
        external_ref=request.external_ref,
        pipeline_slug=request.pipeline,
        name=request.name,
        workflow_repository=domain.workflow_repository,
        case_repository=domain.workflow_case_repository,
        pipeline_repository=domain.pipeline_repository,
    ).execute()

    if result.created:
        # Evento solo en creación real (idempotencia); el caso ya está
        # commiteado (atomic_transaction del repo) antes de despachar.
        try:
            from src.workflows.infrastructure.services.webhooks.case_event_dispatcher import (
                CaseEventDispatcher,
            )

            await CaseEventDispatcher(
                session_maker=get_database_config().session_maker
            ).dispatch(
                DispatchCaseEventInput(
                    tenant_id=tenant.uuid,
                    workflow_id=result.case.workflow_id,
                    case_id=result.case.uuid,
                    event_type=WebhookEventType.CASE_CREATED.value,
                    error={"externalRef": result.case.external_ref, "name": result.case.name},
                )
            )
        except Exception:  # noqa: BLE001 — el webhook jamás rompe la creación
            logger.exception("case.created_dispatch_failed", case_id=str(result.case.uuid))

        # E4 · diseño §3: si la receta sellada espera documentos, el caso tiene
        # su run CASE# desde el nacimiento (best-effort — jamás rompe el POST).
        try:
            await EnsureCaseRunStarted(
                tenant_id=tenant.uuid,
                case_id=result.case.uuid,
                case_repository=domain.workflow_case_repository,
                pipeline_repository=domain.pipeline_repository,
                workflow_repository=domain.workflow_repository,
                temporal_client=temporal_client,
                task_queue=settings.TEMPORAL_TASK_QUEUE,
            ).execute()
        except Exception:  # noqa: BLE001
            logger.exception("case.case_run_start_failed", case_id=str(result.case.uuid))

    return ApiJSONResponse(
        content=_present_case(result.case),
        status_code=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
    )


async def submit_case_data(
    case_id: UUID,
    request: SubmitCaseDataRequest,
    session: AsyncSessionDep,
    domain: DomainContextDep,
    temporal_client: TemporalClientDep,
    tenant: Tenant = Depends(get_tenant_from_api_key),
) -> ApiJSONResponse:
    result = await SubmitCaseData(
        tenant_id=tenant.uuid,
        case_id=case_id,
        doc_type_slug=request.doc_type,
        payload=request.payload,
        auto_start=request.auto_start,
        case_repository=domain.workflow_case_repository,
        document_repository=domain.document_repository,
        document_type_repository=domain.document_type_repository,
        pipeline_repository=domain.pipeline_repository,
        workflow_repository=domain.workflow_repository,
        temporal_client=temporal_client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
    ).execute()
    return ApiJSONResponse(
        content={
            "case_id": str(case_id),
            "document_id": str(result.document.uuid),
            "job_id": result.job_id or None,
            "auto_started": bool(result.job_id),
        },
        status_code=status.HTTP_202_ACCEPTED,
    )


async def get_case(
    case_id: UUID,
    session: AsyncSessionDep,
    domain: DomainContextDep,
    tenant: Tenant = Depends(get_tenant_from_api_key),
) -> ApiJSONResponse:
    aggregate = await GetCaseM2M(
        tenant_id=tenant.uuid,
        case_id=case_id,
        case_repository=domain.workflow_case_repository,
        document_repository=domain.document_repository,
        run_repository=domain.workflow_analysis_run_repository,
        summary_repository=domain.run_summary_repository,
        case_event_repository=domain.case_event_repository,
    ).execute()
    return ApiJSONResponse(content=_present_case_aggregate(aggregate), status_code=status.HTTP_200_OK)


async def get_case_completeness(
    case_id: UUID,
    session: AsyncSessionDep,
    domain: DomainContextDep,
    tenant: Tenant = Depends(get_tenant_from_api_key),
) -> ApiJSONResponse:
    result = await EvaluateCaseCompleteness(
        tenant_id=tenant.uuid,
        case_id=case_id,
        case_repository=domain.workflow_case_repository,
        document_repository=domain.document_repository,
        document_type_repository=domain.document_type_repository,
        pipeline_repository=domain.pipeline_repository,
        workflow_repository=domain.workflow_repository,
        persist=False,
    ).execute()
    return ApiJSONResponse(content=_present_completeness(result), status_code=status.HTTP_200_OK)


async def ready_case(
    case_id: UUID,
    request: ReadyCaseRequest,
    session: AsyncSessionDep,
    domain: DomainContextDep,
    temporal_client: TemporalClientDep,
    tenant: Tenant = Depends(get_tenant_from_api_key),
) -> ApiJSONResponse:
    result = await RequestCaseReady(
        tenant_id=tenant.uuid,
        case_id=case_id,
        case_repository=domain.workflow_case_repository,
        document_repository=domain.document_repository,
        document_type_repository=domain.document_type_repository,
        pipeline_repository=domain.pipeline_repository,
        workflow_repository=domain.workflow_repository,
        temporal_client=temporal_client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        force=request.force,
    ).execute()
    return ApiJSONResponse(
        content={
            "caseId": str(case_id),
            "outcome": result.outcome,
            "readyAt": result.case.ready_at.isoformat() if result.case.ready_at else None,
        },
        status_code=status.HTTP_200_OK,
    )


async def get_case_output(
    case_id: UUID,
    session: AsyncSessionDep,
    domain: DomainContextDep,
    tenant: Tenant = Depends(get_tenant_from_api_key),
) -> ApiJSONResponse:
    run, summary = await GetCaseOutputM2M(
        tenant_id=tenant.uuid,
        case_id=case_id,
        case_repository=domain.workflow_case_repository,
        run_repository=domain.workflow_analysis_run_repository,
        summary_repository=domain.run_summary_repository,
    ).execute()
    return ApiJSONResponse(
        content={
            "case_id": str(case_id),
            "run_id": str(run.uuid),
            "verdict": summary.verdict.value if summary.verdict else None,
            "confidence_score": summary.confidence_score,
            "narrative_status": summary.narrative_status.value if summary.narrative_status else None,
            "output": summary.output,
            "output_schema": summary.output_schema_snapshot,
            "output_provenance": summary.output_provenance,
        },
        status_code=status.HTTP_200_OK,
    )


# ── Router ──────────────────────────────────────────────────────────────────
m2m_cases_router = APIRouter(prefix="", tags=["M2M"])

m2m_cases_router.add_api_route(
    "/cases",
    create_case,
    methods=["POST"],
    summary="Find-or-create case by external_ref (E3 · plano 2)",
)
m2m_cases_router.add_api_route(
    "/cases/{case_id}/data",
    submit_case_data,
    methods=["POST"],
    summary="Inject validated data as a virtual document (+auto-start)",
)
m2m_cases_router.add_api_route(
    "/cases/{case_id}/completeness",
    get_case_completeness,
    methods=["GET"],
    summary="Fresh completeness vs the sealed CompletenessPolicy (E4)",
)
m2m_cases_router.add_api_route(
    "/cases/{case_id}/ready",
    ready_case,
    methods=["POST"],
    summary="Mark case ready (idempotent; 409 case.not_complete unless force)",
)
m2m_cases_router.add_api_route(
    "/cases/{case_id}",
    get_case,
    methods=["GET"],
    summary="Case state + documents + runs + timeline (composed view, E3/E4)",
)
m2m_cases_router.add_api_route(
    "/cases/{case_id}/output",
    get_case_output,
    methods=["GET"],
    summary="Final case output from the latest completed run",
)
