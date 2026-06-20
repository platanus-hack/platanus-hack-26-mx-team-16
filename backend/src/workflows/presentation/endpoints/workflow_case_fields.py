"""Inspection Bench: verificación por campo + comentarios del caso (E5 · §4).

``PATCH /workflows/{wid}/cases/{cid}/documents/{doc_id}/fields`` — body single
u lista, ``action`` correct|accept. ``POST /workflows/{wid}/cases/{cid}/comments``
— case_event ``comment.added`` (el timeline ya lo pinta). Ambos gateados por la
matriz rol×acción (``operate``) a nivel de ruta en el router.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import Depends, status
from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.workflow import WorkflowPermission
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
from src.workflows.application.workflow_cases.commenter import AddCaseComment
from src.workflows.application.workflow_documents.verify_field import (
    FieldVerification,
    VerifyDocumentField,
)
from src.workflows.infrastructure.repositories.sql_human_task import SQLHumanTaskRepository
from src.workflows.presentation.presenters.workflow_document import WorkflowDocumentPresenter


class FieldPatchItem(BaseModel):
    # Alias explícito: el middleware camel→snake de requests es un no-op
    # (BaseHTTPMiddleware no puede reemplazar el body vía request._receive),
    # así que el contrato camelCase del FE se honra con aliases pydantic.
    model_config = ConfigDict(populate_by_name=True)

    field_path: str = Field(..., min_length=1, max_length=255, alias="fieldPath")
    action: Literal["correct", "accept"] = "correct"
    value: Any = None


class AddCaseCommentRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


async def patch_case_document_fields(
    workflow_id: UUID,
    case_id: UUID,
    document_id: UUID,
    request: FieldPatchItem | list[FieldPatchItem],
    session: AsyncSessionDep,
    temporal_client: TemporalClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    """Corrige/acepta campos del documento (E5 §4): 404 binding, 423 lock,
    503 si la señal ``corrections`` al run pausado falla."""
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    items = request if isinstance(request, list) else [request]
    result = await VerifyDocumentField(
        tenant_id=tenant.uuid,
        case_id=case_id,
        document_id=document_id,
        fields=[
            FieldVerification(field_path=i.field_path, action=i.action, value=i.value)
            for i in items
        ],
        verified_by=f"user:{current_tenant_user.user_id}",
        case_repository=app_context.domain.workflow_case_repository,
        document_repository=app_context.domain.document_repository,
        case_event_repository=app_context.domain.case_event_repository,
        human_task_repository=SQLHumanTaskRepository(session),
        temporal_client=temporal_client,
        workflow_id=workflow_id,
    ).execute()
    return ApiJSONResponse(
        content={
            "document": WorkflowDocumentPresenter(instance=result.document).to_dict,
            "verified_fields": result.verified_paths,
            "level": result.level,
            "corrections_signaled": result.corrections_signaled,
        },
        status_code=status.HTTP_200_OK,
    )


async def add_case_comment(
    workflow_id: UUID,
    case_id: UUID,
    request: AddCaseCommentRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    event = await AddCaseComment(
        tenant_id=tenant.uuid,
        case_id=case_id,
        body=request.body,
        case_repository=app_context.domain.workflow_case_repository,
        case_event_repository=app_context.domain.case_event_repository,
        actor=f"user:{current_tenant_user.user_id}",
        workflow_id=workflow_id,
    ).execute()
    # Shape del timeline (E4): el FE lo inserta tal cual.
    return ApiJSONResponse(
        content={
            "uuid": str(event.uuid),
            "type": event.type,
            "payload": event.payload,
            "actor": event.actor,
            "createdAt": event.created_at.isoformat() if event.created_at else None,
        },
        status_code=status.HTTP_201_CREATED,
    )
