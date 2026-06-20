"""Duplicate workflow endpoint — ADR 0002 · §3.7.

``POST /v1/workflows/{id}/duplicate`` (gated ``manage`` sobre el origen + permiso
tenant ``create``): deep-copy del workflow vía la maquinaria export/import. El
duplicado nace con su pipeline propio (cero refs compartidas) y se programa la
recompilación de sus reglas, igual que el import de bundle.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import BackgroundTasks, Depends, Request, status
from pydantic import BaseModel, Field

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.workflow import WorkflowPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.tenant import (
    get_required_tenant,
    get_required_tenant_user,
)
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.application.workflow_rules.compilation.background import (
    schedule_and_run_compilation,
)
from src.workflows.application.workflows.capabilities_resolver import (
    WorkflowCapabilitiesResolver,
    capabilities_to_payload,
)
from src.workflows.application.workflows.duplicate import DuplicateWorkflow
from src.workflows.presentation.presenters.workflow import WorkflowPresenter


class DuplicateWorkflowRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


async def duplicate_workflow(
    workflow_id: UUID,
    request: DuplicateWorkflowRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.create])
    use_case = DuplicateWorkflow(
        source_workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        new_name=request.name,
        created_by_id=current_tenant_user.user_id,
        workflow_repository=app_context.domain.workflow_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
        rule_repository=app_context.domain.workflow_rule_repository,
        document_type_repository=app_context.domain.document_type_repository,
        kb_document_repository=app_context.domain.kb_document_repository,
        tool_repository=app_context.domain.tool_repository,
    )
    new_workflow = await use_case.execute()

    for rule_id in use_case.rule_ids_to_recompile or []:
        background_tasks.add_task(
            schedule_and_run_compilation,
            rule_id,
            tenant.uuid,
            new_workflow.uuid,
            http_request.app.state.database_config,
            http_request.app.state.redis_client,
            http_request.app.state.event_publisher,
        )
    capabilities = await WorkflowCapabilitiesResolver(
        pipeline_repository=app_context.domain.pipeline_repository
    ).for_workflow(new_workflow)
    return ApiJSONResponse(
        content=WorkflowPresenter(
            instance=new_workflow, capabilities=capabilities_to_payload(capabilities)
        ).to_dict,
        status_code=status.HTTP_201_CREATED,
    )
