"""Router ``/staff/v1`` (ADR 0001 — los 5 endpoints mínimos, nada más).

Tercer plano de auth del sistema (junto a JWT+X-Tenant y M2M X-Api-Key):
TODO el router está gateado por ``get_staff_user`` (claim + fila activa) vía
la dependencia de audit, rechaza ``X-Tenant`` con 400 y escribe
``staff_access_events`` en el 100 % de las requests (middleware de router).
Cualquier ampliación de alcance requiere un ADR que reemplace al 0001.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi import status as http_status
from pydantic import BaseModel, Field

from src.common.infrastructure.dependencies.common import AsyncSessionDep, TemporalClientDep
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.staff.application.audit import ListStaffAudit
from src.staff.application.case_read import GetCaseReadOnly
from src.staff.application.claim import ClaimL1Task
from src.staff.application.metrics import GetStaffMetrics
from src.staff.application.queue import ListL1Queue
from src.staff.application.resolve import ResolveL1Task
from src.staff.infrastructure.repositories.sql_staff_access_event import (
    SQLStaffAccessEventRepository,
)
from src.staff.infrastructure.repositories.sql_staff_case_reader import SQLStaffCaseReader
from src.staff.infrastructure.repositories.sql_staff_human_task import (
    SQLStaffHumanTaskRepository,
)
from src.staff.presentation.dependencies import (
    StaffUserDep,
    reject_tenant_header,
    staff_audit,
)
from src.staff.presentation.presenters import (
    present_access_event,
    present_case_aggregate,
    present_metrics,
    present_queue_item,
    present_task,
)
from src.workflows.infrastructure.repositories.sql_case_event import SQLCaseEventRepository
from src.workflows.infrastructure.repositories.sql_document_repository import (
    SQLWorkflowDocumentRepository,
)
from src.workflows.infrastructure.repositories.sql_human_task import SQLHumanTaskRepository


class ClaimTaskRequest(BaseModel):
    release: bool = False


class ResolveTaskRequest(BaseModel):
    resolution: dict = Field(default_factory=dict)


async def list_tasks(
    session: AsyncSessionDep,
    staff_user: StaffUserDep,
    tenant: UUID | None = None,
    status: str | None = "pending",
    limit: int = 200,
    kind: str | None = None,
) -> ApiJSONResponse:
    items = await ListL1Queue(
        repository=SQLStaffHumanTaskRepository(session),
        tenant_id=tenant,
        status=status,
        limit=min(limit, 500),
        # E6 §3: ?kind=qa segmenta la auditoría QA; ?kind=approval las aprobaciones.
        kind=kind,
    ).execute()
    return ApiJSONResponse(
        content=[present_queue_item(item) for item in items],
        status_code=http_status.HTTP_200_OK,
    )


async def claim_task(
    task_id: UUID,
    payload: ClaimTaskRequest,
    request: Request,
    session: AsyncSessionDep,
    staff_user: StaffUserDep,
) -> ApiJSONResponse:
    task = await ClaimL1Task(
        task_id=task_id,
        staff_user=staff_user,
        repository=SQLStaffHumanTaskRepository(session),
        release=payload.release,
    ).execute()
    # Enriquecer el audit del request (el tenant sale de la fila).
    request.state.staff_audit_tenant_id = task.tenant_id
    request.state.staff_audit_case_id = task.case_id
    return ApiJSONResponse(content=present_task(task), status_code=http_status.HTTP_200_OK)


async def resolve_task(
    task_id: UUID,
    payload: ResolveTaskRequest,
    request: Request,
    session: AsyncSessionDep,
    temporal_client: TemporalClientDep,
    staff_user: StaffUserDep,
) -> ApiJSONResponse:
    task = await ResolveL1Task(
        task_id=task_id,
        staff_user=staff_user,
        resolution=payload.resolution,
        staff_task_repository=SQLStaffHumanTaskRepository(session),
        human_task_repository=SQLHumanTaskRepository(session),
        temporal_client=temporal_client,
        # E5 §3.4: invariante open_flags también en L1 (409 + force).
        document_repository=SQLWorkflowDocumentRepository(session=session),
        # E6 §3: registro del veredicto QA cuando la task es kind=QA.
        case_event_repository=SQLCaseEventRepository(session),
    ).execute()
    request.state.staff_audit_tenant_id = task.tenant_id
    request.state.staff_audit_case_id = task.case_id
    return ApiJSONResponse(content=present_task(task), status_code=http_status.HTTP_200_OK)


async def get_case(
    case_id: UUID,
    request: Request,
    session: AsyncSessionDep,
    staff_user: StaffUserDep,
) -> ApiJSONResponse:
    aggregate = await GetCaseReadOnly(
        case_id=case_id,
        staff_user=staff_user,
        reader=SQLStaffCaseReader(session),
        task_repository=SQLStaffHumanTaskRepository(session),
    ).execute()
    request.state.staff_audit_tenant_id = aggregate.case.tenant_id
    return ApiJSONResponse(
        content=present_case_aggregate(aggregate),
        status_code=http_status.HTTP_200_OK,
    )


async def get_audit(
    session: AsyncSessionDep,
    staff_user: StaffUserDep,
    staff_user_id: UUID | None = None,
    tenant: UUID | None = None,
    action: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> ApiJSONResponse:
    events = await ListStaffAudit(
        actor=staff_user,
        repository=SQLStaffAccessEventRepository(session),
        staff_user_id=staff_user_id,
        tenant_id=tenant,
        action=action,
        limit=min(limit, 500),
        offset=offset,
    ).execute()
    return ApiJSONResponse(
        content=[present_access_event(e) for e in events],
        status_code=http_status.HTTP_200_OK,
    )


async def get_metrics(
    session: AsyncSessionDep,
    staff_user: StaffUserDep,
    tenant: UUID | None = None,
    since: datetime | None = None,
) -> ApiJSONResponse:
    metrics = await GetStaffMetrics(
        actor=staff_user,
        repository=SQLCaseEventRepository(session),
        since=since,
        tenant_id=tenant,
    ).execute()
    return ApiJSONResponse(
        content=present_metrics(metrics),
        status_code=http_status.HTTP_200_OK,
    )


# Orden de dependencias: X-Tenant ⇒ 400 primero; luego auth staff + audit
# (staff_audit depende de get_staff_user — gate por construcción).
staff_router = APIRouter(
    tags=["staff"],
    dependencies=[Depends(reject_tenant_header), Depends(staff_audit)],
)

staff_router.add_api_route(
    "/tasks",
    list_tasks,
    methods=["GET"],
    summary="Unified cross-tenant L1 review queue (staff)",
)
staff_router.add_api_route(
    "/tasks/{task_id}/claim",
    claim_task,
    methods=["POST"],
    summary="Claim/release an L1 task (pessimistic lock)",
)
staff_router.add_api_route(
    "/tasks/{task_id}/resolve",
    resolve_task,
    methods=["POST"],
    summary="Resolve an L1 task as staff (signals the pipeline run)",
)
staff_router.add_api_route(
    "/cases/{case_id}",
    get_case,
    methods=["GET"],
    summary="Read-only case aggregate for the task at hand",
)
staff_router.add_api_route(
    "/audit",
    get_audit,
    methods=["GET"],
    summary="Staff access audit log (staff_admin only)",
)
staff_router.add_api_route(
    "/metrics",
    get_metrics,
    methods=["GET"],
    summary="QA metrics: qa.passed/failed + review.approved/skipped (staff_admin only)",
)
