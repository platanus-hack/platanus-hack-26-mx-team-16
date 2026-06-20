"""Workflow rule compilation endpoints — UseCase + Presenter pattern (spec §11)."""

from __future__ import annotations

from uuid import UUID

from fastapi import BackgroundTasks, Depends, Request, status

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
from src.workflows.application.workflow_rules.compilation.lister import (
    WorkflowRuleCompilationLister,
)
from src.workflows.application.workflow_rules.getter import WorkflowRuleGetter
from src.workflows.presentation.presenters.workflow_rule_compilation import (
    WorkflowRuleCompilationPresenter,
)


async def list_compilations(
    rule_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    compilations = await WorkflowRuleCompilationLister(
        rule_id=rule_id,
        tenant_id=tenant.uuid,
        rule_repository=app_context.domain.workflow_rule_repository,
        compilation_repository=app_context.domain.workflow_rule_compilation_repository,
    ).execute()
    return ApiJSONResponse(
        content=[WorkflowRuleCompilationPresenter(instance=c).to_dict for c in compilations],
        status_code=status.HTTP_200_OK,
    )


async def recompile_rule(
    rule_id: UUID,
    background_tasks: BackgroundTasks,
    http_request: Request,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    rule = await WorkflowRuleGetter(
        rule_id=rule_id,
        tenant_id=tenant.uuid,
        rule_repository=app_context.domain.workflow_rule_repository,
    ).execute()

    background_tasks.add_task(
        schedule_and_run_compilation,
        rule.uuid,
        tenant.uuid,
        rule.workflow_id,
        http_request.app.state.database_config,
        http_request.app.state.redis_client,
        http_request.app.state.event_publisher,
    )
    return ApiJSONResponse(
        content={"status": "scheduled"},
        status_code=status.HTTP_202_ACCEPTED,
    )
