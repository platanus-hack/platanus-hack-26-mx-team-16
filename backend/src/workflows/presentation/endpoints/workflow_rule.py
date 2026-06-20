"""Workflow rule CRUD endpoints — UseCase + Presenter pattern (spec §11)."""

from __future__ import annotations

from uuid import UUID

from fastapi import BackgroundTasks, Depends, Request, status
from sse_starlette.sse import EventSourceResponse

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.workflow import WorkflowPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import (
    RedisClientDep,
    get_app_context,
)
from src.common.infrastructure.dependencies.tenant import (
    get_required_tenant,
    get_required_tenant_user,
)
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.infrastructure.sse.streaming import stream_sse
from src.workflows.application.workflow_rules.compilation.background import (
    schedule_and_run_compilation,
)
from src.workflows.application.workflow_rules.compilation.clearer import (
    WorkflowRuleCompilationClearer,
)
from src.workflows.application.workflow_rules.compilation.state_getter import (
    WorkflowCompilingRulesStateGetter,
)
from src.workflows.application.workflow_rules.creator import WorkflowRuleCreator
from src.workflows.application.workflow_rules.deleter import WorkflowRuleDeleter
from src.workflows.application.workflow_rules.getter import WorkflowRuleGetter
from src.workflows.application.workflow_rules.lister import WorkflowRuleLister
from src.workflows.application.workflow_rules.reorderer import WorkflowRulesReorderer
from src.workflows.application.workflow_rules.updater import WorkflowRuleUpdater
from src.workflows.application.workflows.getter import WorkflowGetter
from src.workflows.domain.rules.events import channel_for_workflow_rules
from src.workflows.presentation.presenters.workflow_rule import WorkflowRulePresenter
from src.workflows.presentation.schemas.workflow_rule import (
    CreateWorkflowRuleRequest,
    ReorderWorkflowRulesRequest,
    UpdateWorkflowRuleRequest,
)


async def list_rules(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    rules = await WorkflowRuleLister(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        rule_repository=app_context.domain.workflow_rule_repository,
    ).execute()
    return ApiJSONResponse(
        content=[WorkflowRulePresenter(instance=r).to_dict for r in rules],
        status_code=status.HTTP_200_OK,
    )


async def get_rule(
    rule_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    rule = await WorkflowRuleGetter(
        rule_id=rule_id,
        tenant_id=tenant.uuid,
        rule_repository=app_context.domain.workflow_rule_repository,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowRulePresenter(instance=rule).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def create_rule(
    workflow_id: UUID,
    request: CreateWorkflowRuleRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    rule = await WorkflowRuleCreator(
        tenant_id=tenant.uuid,
        workflow_id=workflow_id,
        name=request.name,
        kind=request.kind,
        prompt=request.prompt,
        when=request.when,
        config=request.config,
        scope=request.scope,
        knowledge_refs=request.knowledge_refs,
        is_active=request.is_active,
        rule_repository=app_context.domain.workflow_rule_repository,
        workflow_repository=app_context.domain.workflow_repository,
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
        content=WorkflowRulePresenter(instance=rule).to_dict,
        status_code=status.HTTP_201_CREATED,
    )


async def update_rule(
    rule_id: UUID,
    request: UpdateWorkflowRuleRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    outcome = await WorkflowRuleUpdater(
        rule_id=rule_id,
        tenant_id=tenant.uuid,
        rule_repository=app_context.domain.workflow_rule_repository,
        name=request.name,
        is_active=request.is_active,
        kind=request.kind,
        prompt=request.prompt,
        when=request.when,
        config=request.config,
        scope=request.scope,
        knowledge_refs=request.knowledge_refs,
    ).execute()

    if outcome.needs_recompilation:
        if outcome.rule.current_compilation_id:
            await WorkflowRuleCompilationClearer(
                compilation_id=outcome.rule.current_compilation_id,
                compilation_repository=app_context.domain.workflow_rule_compilation_repository,
            ).execute()
        background_tasks.add_task(
            schedule_and_run_compilation,
            outcome.rule.uuid,
            tenant.uuid,
            outcome.rule.workflow_id,
            http_request.app.state.database_config,
            http_request.app.state.redis_client,
            http_request.app.state.event_publisher,
        )

    return ApiJSONResponse(
        content=WorkflowRulePresenter(instance=outcome.rule).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def delete_rule(
    rule_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.delete])
    await WorkflowRuleDeleter(
        rule_id=rule_id,
        tenant_id=tenant.uuid,
        rule_repository=app_context.domain.workflow_rule_repository,
    ).execute()
    return ApiJSONResponse(content=None, status_code=status.HTTP_204_NO_CONTENT)


async def reorder_rules(
    workflow_id: UUID,
    request: ReorderWorkflowRulesRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    rules = await WorkflowRulesReorderer(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        ordered_rule_ids=request.rule_ids,
        rule_repository=app_context.domain.workflow_rule_repository,
    ).execute()
    return ApiJSONResponse(
        content=[WorkflowRulePresenter(instance=r).to_dict for r in rules],
        status_code=status.HTTP_200_OK,
    )


async def get_compiling_state(
    workflow_id: UUID,
    redis_client: RedisClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    rule_ids = await WorkflowCompilingRulesStateGetter(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        workflow_repository=app_context.domain.workflow_repository,
        redis_client=redis_client,
    ).execute()
    return ApiJSONResponse(
        content={"rule_ids": rule_ids},
        status_code=status.HTTP_200_OK,
    )


async def stream_workflow_rule_events(
    workflow_id: UUID,
    request: Request,
    redis_client: RedisClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> EventSourceResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    await WorkflowGetter(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        workflow_repository=app_context.domain.workflow_repository,
    ).execute()
    return stream_sse(
        channel=channel_for_workflow_rules(workflow_id),
        redis_client=redis_client,
        request=request,
    )
