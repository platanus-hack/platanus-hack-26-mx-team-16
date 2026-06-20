"""Endpoints to list workflow-rule-results of a run — UseCase + Presenter pattern (spec §11)."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, status

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
from src.workflows.application.workflow_rules.results.lister import WorkflowRuleResultsLister
from src.workflows.presentation.presenters.workflow_rule_result import (
    WorkflowRuleResultPresenter,
)


async def list_run_results(
    run_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    results = await WorkflowRuleResultsLister(
        run_id=run_id,
        tenant_id=tenant.uuid,
        run_repository=app_context.domain.workflow_analysis_run_repository,
        result_repository=app_context.domain.workflow_rule_result_repository,
    ).execute()
    # Resolve rule names so each card surfaces the rule title.
    run = await app_context.domain.workflow_analysis_run_repository.find_by_id(run_id, tenant.uuid)
    rule_names: dict = {}
    if run is not None:
        rules = await app_context.domain.workflow_rule_repository.list_by_workflow(run.workflow_id, tenant.uuid)
        rule_names = {r.uuid: r.name for r in rules}
    return ApiJSONResponse(
        content=[
            WorkflowRuleResultPresenter(instance=r, rule_name=rule_names.get(r.rule_id)).to_dict for r in results
        ],
        status_code=status.HTTP_200_OK,
    )
