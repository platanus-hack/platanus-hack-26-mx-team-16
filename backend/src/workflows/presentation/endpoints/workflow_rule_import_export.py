"""Workflow-rule import/export endpoints — UseCase + Presenter pattern (spec §14.5)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query, status

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
from src.workflows.application.workflow_rules.import_export.exporter import WorkflowRulesExporter
from src.workflows.application.workflow_rules.import_export.importer import (
    ImportConflictStrategy,
    WorkflowRulesImporter,
)
from src.workflows.presentation.presenters.workflow_rule_import_report import (
    WorkflowRuleImportReportPresenter,
)
from src.workflows.presentation.schemas.workflow_rule import ImportWorkflowRulesRequest


async def export_workflow_rules(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    payload = await WorkflowRulesExporter(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        rule_repository=app_context.domain.workflow_rule_repository,
        document_type_repository=app_context.domain.document_type_repository,
        kb_document_repository=app_context.domain.kb_document_repository,
    ).execute()
    return ApiJSONResponse(content=payload, status_code=status.HTTP_200_OK)


async def preview_workflow_rules_import(
    workflow_id: UUID,
    request: ImportWorkflowRulesRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    report = await WorkflowRulesImporter(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        payload=request.payload,
        strategy=ImportConflictStrategy.SKIP,
        workflow_repository=app_context.domain.workflow_repository,
        rule_repository=app_context.domain.workflow_rule_repository,
        document_type_repository=app_context.domain.document_type_repository,
        kb_document_repository=app_context.domain.kb_document_repository,
        dry_run=True,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowRuleImportReportPresenter(instance=report).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def import_workflow_rules(
    workflow_id: UUID,
    request: ImportWorkflowRulesRequest,
    strategy: Annotated[ImportConflictStrategy, Query()] = ImportConflictStrategy.SKIP,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    report = await WorkflowRulesImporter(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        payload=request.payload,
        strategy=strategy,
        workflow_repository=app_context.domain.workflow_repository,
        rule_repository=app_context.domain.workflow_rule_repository,
        document_type_repository=app_context.domain.document_type_repository,
        kb_document_repository=app_context.domain.kb_document_repository,
        dry_run=False,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowRuleImportReportPresenter(instance=report).to_dict,
        status_code=status.HTTP_200_OK,
    )
