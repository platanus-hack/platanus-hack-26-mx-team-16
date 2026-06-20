"""HumanTask review-queue endpoints (F6 · endurecidos en E5 §3.2).

Toda la superficie tenant exige usuario autenticado (JWT + tenant user) — el
hallazgo del recon (solo X-Tenant) queda cerrado. Claim/release con UPDATE
condicional (lock pesimista); resolve valida holder, hace auto-claim, aplica
la validación de stage (L1 = solo staff; L2 = acción ``approve`` de la matriz
rol×acción) y el invariante open_flags (§3.4).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from src.common.domain.exceptions._base import DomainError
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.workflow_actions import (
    WorkflowActionForbiddenError,
    workflow_role_allows,
)
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import (
    AsyncSessionDep,
    TemporalClientDep,
    get_app_context,
)
from src.common.infrastructure.dependencies.tenant import (
    get_required_tenant,
    get_required_tenant_user,
)
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.application.human_tasks.claim import ClaimHumanTask
from src.workflows.application.human_tasks.resolve import (
    HumanTaskClaimConflictError,
    ResolveHumanTask,
)
from src.workflows.application.workflow_members.role_resolver import (
    ResolveWorkflowRole,
    is_tenant_admin,
)
from src.workflows.domain.models.human_task import HumanTask
from src.workflows.infrastructure.repositories.sql_human_task import SQLHumanTaskRepository

human_tasks_router = APIRouter(prefix="/human-tasks", tags=["HumanTasks"])

STAFF_ONLY_STAGE = "review_l1"
APPROVE_REQUIRED_STAGE = "review_l2"


class HumanTaskStageForbiddenError(DomainError):
    """E5 §3.2: el stage L1 se resuelve en la consola staff, no en tenant."""

    def __init__(self, task_id: str, stage: str):
        super().__init__(
            code="human_task.stage_forbidden",
            message=f"Tasks in stage '{stage}' are resolved by Doxiq staff.",
            status_code=403,
            context={"task_id": task_id, "stage": stage},
        )


class ResolveHumanTaskRequest(BaseModel):
    resolution: dict = Field(default_factory=dict)


class ClaimHumanTaskRequest(BaseModel):
    release: bool = False


def _present(task: HumanTask, workflow_slugs: dict[UUID, str] | None = None) -> dict:
    slugs = workflow_slugs or {}
    return {
        "uuid": str(task.uuid),
        "task_key": task.task_key,
        "kind": task.kind.value,
        "status": task.status.value,
        "assignee_mode": task.assignee_mode.value,
        "audience": task.audience,
        "case_id": str(task.case_id) if task.case_id else None,
        "workflow_id": str(task.workflow_id) if task.workflow_id else None,
        # E4: la cola /review navega a /workflows/{slug}/cases/{caseId} — el
        # slug viaja aquí para no obligar al FE a resolver uuid→slug.
        "workflow_slug": slugs.get(task.workflow_id) if task.workflow_id else None,
        "payload": task.payload,
        # E5: colas L1/L2 + lock visible (holder del claim) en el FE.
        "stage": task.stage,
        "claimed_by": task.claimed_by,
        "claimed_at": task.claimed_at.isoformat() if task.claimed_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


async def _workflow_slugs_for(session, tenant_id: UUID, tasks: list[HumanTask]) -> dict[UUID, str]:
    workflow_ids = {t.workflow_id for t in tasks if t.workflow_id}
    if not workflow_ids:
        return {}
    from sqlalchemy import select

    from src.common.database.models.workspace import WorkflowORM

    result = await session.execute(
        select(WorkflowORM.uuid, WorkflowORM.slug).where(
            WorkflowORM.uuid.in_(workflow_ids),
            WorkflowORM.tenant_id == tenant_id,
        )
    )
    return {row.uuid: row.slug for row in result}


async def list_human_tasks(
    session: AsyncSessionDep,
    audience: str | None = None,
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    # E5 §3.2: superficie endurecida — exige usuario autenticado del tenant.
    tasks = await SQLHumanTaskRepository(session).list_open(tenant.uuid, audience)
    slugs = await _workflow_slugs_for(session, tenant.uuid, tasks)
    return ApiJSONResponse(content=[_present(t, slugs) for t in tasks], status_code=status.HTTP_200_OK)


async def _assert_stage_resolvable(
    task: HumanTask,
    tenant: Tenant,
    current_tenant_user: TenantUser,
    app_context: AppContext,
) -> None:
    """Validación de stage (E5 §3.2): L1 = solo staff; L2 = acción ``approve``
    de la matriz rol×acción del workflow de la tarea."""
    if task.stage == STAFF_ONLY_STAGE:
        raise HumanTaskStageForbiddenError(str(task.uuid), task.stage)
    if task.stage == APPROVE_REQUIRED_STAGE and task.workflow_id is not None:
        role = await ResolveWorkflowRole(
            workflow_id=task.workflow_id,
            tenant_id=tenant.uuid,
            tenant_user=current_tenant_user,
            workflow_repository=app_context.domain.workflow_repository,
            member_repository=app_context.domain.workflow_member_repository,
        ).execute()
        if not workflow_role_allows(role, "approve"):
            raise WorkflowActionForbiddenError("approve", str(task.workflow_id), role)


async def claim_human_task(
    task_id: UUID,
    request: ClaimHumanTaskRequest,
    session: AsyncSessionDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    """Claim/release pesimista (E5 §3.2): UPDATE condicional; reclamada por
    otro ⇒ 409 ``human_task.already_claimed`` con el holder."""
    repository = SQLHumanTaskRepository(session)
    existing = await repository.find_by_id(task_id, tenant.uuid)
    if existing is None:
        return ApiJSONResponse(content={"detail": "Human task not found"}, status_code=status.HTTP_404_NOT_FOUND)
    # El claim respeta la misma validación de stage que el resolve (L1 staff;
    # L2 exige `approve`): nadie bloquea una cola que no puede resolver.
    await _assert_stage_resolvable(existing, tenant, current_tenant_user, app_context)

    task = await ClaimHumanTask(
        task_id=task_id,
        tenant_id=tenant.uuid,
        actor=f"user:{current_tenant_user.user_id}",
        repository=repository,
        release=request.release,
        force_release=request.release and is_tenant_admin(current_tenant_user),
    ).execute()
    return ApiJSONResponse(content=_present(task), status_code=status.HTTP_200_OK)


async def resolve_human_task(
    task_id: UUID,
    request: ResolveHumanTaskRequest,
    session: AsyncSessionDep,
    temporal_client: TemporalClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    repository = SQLHumanTaskRepository(session)
    existing = await repository.find_by_id(task_id, tenant.uuid)
    if existing is None:
        return ApiJSONResponse(content={"detail": "Human task not found"}, status_code=status.HTTP_404_NOT_FOUND)
    await _assert_stage_resolvable(existing, tenant, current_tenant_user, app_context)

    actor = f"user:{current_tenant_user.user_id}"
    if existing.status.value == "pending":
        # Auto-claim implícito al resolver (E5 §3.2): el UPDATE condicional
        # falla ⇒ otra persona la tiene ⇒ 409 con holder.
        claimed = await repository.claim(task_id, tenant.uuid, actor)
        if claimed is None:
            fresh = await repository.find_by_id(task_id, tenant.uuid)
            holder = fresh.claimed_by if fresh else None
            if holder and holder != actor:
                raise HumanTaskClaimConflictError(str(task_id), holder=holder)

    task = await ResolveHumanTask(
        task_id=task_id,
        tenant_id=tenant.uuid,
        resolution=request.resolution,
        repository=repository,
        temporal_client=temporal_client,
        actor=actor,
        # E5 §3.4: invariante open_flags (409 + force) en la aprobación.
        document_repository=app_context.domain.document_repository,
    ).execute()
    if task is None:
        return ApiJSONResponse(content={"detail": "Human task not found"}, status_code=status.HTTP_404_NOT_FOUND)
    return ApiJSONResponse(content=_present(task), status_code=status.HTTP_200_OK)


human_tasks_router.add_api_route(
    "",
    list_human_tasks,
    methods=["GET"],
    summary="List open human tasks for the review queue",
)
human_tasks_router.add_api_route(
    "/{task_id}/claim",
    claim_human_task,
    methods=["POST"],
    summary="Claim or release a human task (pessimistic lock, E5)",
)
human_tasks_router.add_api_route(
    "/{task_id}/resolve",
    resolve_human_task,
    methods=["POST"],
    summary="Resolve a human task and resume its pipeline run",
)
