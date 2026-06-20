"""M2M control endpoints (F9 · W2).

Machine-to-machine surface for partner integrations. Unlike the JWT-admin
endpoints, these resolve the tenant from a ``dxk_`` API key via
``get_tenant_from_api_key`` (``X-Api-Key`` header) instead of
``get_required_tenant`` + ``X-Tenant``.

Mounted at ``/v1`` (the router itself carries an empty prefix), so the routes
are ``/v1/jobs/{job_id}``, ``/v1/tasks/{task_id}/resolve`` and ``/v1/case``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from src.common.domain.exceptions._base import DomainError
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.dependencies.common import AsyncSessionDep, TemporalClientDep
from src.common.infrastructure.dependencies.tenant_api_key import get_tenant_from_api_key
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.application.human_tasks.resolve import ResolveHumanTask
from src.workflows.infrastructure.repositories.sql_document_repository import (
    SQLWorkflowDocumentRepository,
)
from src.workflows.infrastructure.repositories.sql_human_task import SQLHumanTaskRepository
from src.workflows.infrastructure.repositories.sql_workflow_processing_job import (
    SQLWorkflowProcessingJobRepository,
)
from src.workflows.presentation.presenters.m2m_job import present_job


# ── Request models ─────────────────────────────────────────────────────────
class ResolveTaskRequest(BaseModel):
    resolution: dict = Field(default_factory=dict)


# ── Errors ─────────────────────────────────────────────────────────────────
class M2MStageForbiddenError(DomainError):
    """E5 §C4: el M2M (API key) sólo resuelve el gate único E4 (``stage=None``).

    Las tareas de revisión multinivel L1/L2 exigen un actor humano: L1 es
    exclusiva de la consola staff; L2 exige un usuario tenant con acción
    ``approve``. Una API key NUNCA debe poder resolverlas (saltaría el
    stage-gating, el claim-lock y la atribución del timeline)."""

    def __init__(self, task_id: str, stage: str):
        super().__init__(
            code="human_task.stage_forbidden",
            message=f"Tasks in stage '{stage}' cannot be resolved via API key; they require a human reviewer.",
            status_code=403,
            context={"task_id": task_id, "stage": stage},
        )


# ── Endpoints ──────────────────────────────────────────────────────────────
async def get_job_status(
    job_id: str,
    session: AsyncSessionDep,
    tenant: Tenant = Depends(get_tenant_from_api_key),
) -> ApiJSONResponse:
    """Estado + RESULTADO del job (E1 — antes solo estado).

    `documents[*].fields` trae `{value, parse_confidence, source}` por campo
    (capa-1 bbox/OCR); `extraction` es el JSON crudo. El job_id es reusable:
    el resultado persiste y puede consultarse las veces que haga falta.
    """
    processing_job = await SQLWorkflowProcessingJobRepository(session).find_by_temporal_workflow_id(job_id)
    if processing_job is None or processing_job.tenant_id != tenant.uuid:
        return ApiJSONResponse(
            content={"error": "job_not_found", "job_id": job_id},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    documents = await SQLWorkflowDocumentRepository(session).list_by_processing_job(processing_job.uuid)
    return ApiJSONResponse(
        content=present_job(processing_job, documents),
        status_code=status.HTTP_200_OK,
    )


async def resolve_task_m2m(
    task_id: UUID,
    request: ResolveTaskRequest,
    session: AsyncSessionDep,
    temporal_client: TemporalClientDep,
    tenant: Tenant = Depends(get_tenant_from_api_key),
) -> ApiJSONResponse:
    """Resuelve el gate único E4 (``stage=None``) por API key.

    E5 §C4: leemos la tarea ANTES de resolver y rechazamos 403 si tiene stage
    (L1/L2 son human-only). Para el gate que sí sirve pasamos un actor explícito
    (atribución en el timeline) y el repo de documentos (reactiva el invariante
    open_flags §3.4)."""
    repository = SQLHumanTaskRepository(session)
    existing = await repository.find_by_id(task_id, tenant.uuid)
    if existing is None:
        return ApiJSONResponse(
            content={"error": "task_not_found", "task_id": str(task_id)},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if existing.stage is not None:
        raise M2MStageForbiddenError(str(task_id), existing.stage)

    await ResolveHumanTask(
        task_id=task_id,
        tenant_id=tenant.uuid,
        resolution=request.resolution,
        repository=repository,
        temporal_client=temporal_client,
        actor="external:apikey",
        document_repository=SQLWorkflowDocumentRepository(session),
    ).execute()
    return ApiJSONResponse(content={"resolved": True}, status_code=status.HTTP_200_OK)


# ── Router ─────────────────────────────────────────────────────────────────
m2m_router = APIRouter(prefix="", tags=["M2M"])

m2m_router.add_api_route(
    "/jobs/{job_id}",
    get_job_status,
    methods=["GET"],
    summary="Get job status by temporal_workflow_id (F9 · W2)",
)
m2m_router.add_api_route(
    "/tasks/{task_id}/resolve",
    resolve_task_m2m,
    methods=["POST"],
    summary="Resolve a human task via M2M (F9 · W2)",
)
# El stub POST /v1/case (re-entry farmacia-B) fue reemplazado en E3 por
# POST /v1/cases + POST /v1/cases/{id}/data (m2m_cases.py · plan §4.4).
