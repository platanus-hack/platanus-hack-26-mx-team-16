"""Workflow bundle import/export endpoints (E6 · W4 · diseño §4).

* ``GET  /v1/workflows/{id}/export``            — view guard.
* ``POST /v1/workflows/{id}/import/preview``     — dry-run report.
* ``POST /v1/workflows/{id}/import?strategy=``   — apply + schedule recompilation.

The import is transactional per section (NOT all-or-nothing v1 — documented in
the importer). Rule recompilation is scheduled in the background, mirroring the
``recompile_rule`` endpoint.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import BackgroundTasks, Depends, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field

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
from src.workflows.application.workflows.import_export.exporter import (
    WorkflowBundleExporter,
)
from src.workflows.application.workflows.import_export.importer import (
    ImportConflictStrategy,
    WorkflowBundleImporter,
)


class ImportWorkflowBundleRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    payload: dict = Field(default_factory=dict)


async def export_workflow_bundle(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    envelope = await WorkflowBundleExporter(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        workflow_repository=app_context.domain.workflow_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
        rule_repository=app_context.domain.workflow_rule_repository,
        document_type_repository=app_context.domain.document_type_repository,
        kb_document_repository=app_context.domain.kb_document_repository,
    ).execute()
    return ApiJSONResponse(content=envelope, status_code=status.HTTP_200_OK)


async def preview_workflow_bundle_import(
    workflow_id: UUID,
    request: ImportWorkflowBundleRequest,
    strategy: Annotated[ImportConflictStrategy, Query()] = ImportConflictStrategy.SKIP,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    report = await WorkflowBundleImporter(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        payload=request.payload,
        strategy=strategy,
        workflow_repository=app_context.domain.workflow_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
        rule_repository=app_context.domain.workflow_rule_repository,
        document_type_repository=app_context.domain.document_type_repository,
        kb_document_repository=app_context.domain.kb_document_repository,
        dry_run=True,
    ).execute()
    return ApiJSONResponse(content=report.to_dict(), status_code=status.HTTP_200_OK)


async def import_workflow_bundle(
    workflow_id: UUID,
    request: ImportWorkflowBundleRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    strategy: Annotated[ImportConflictStrategy, Query()] = ImportConflictStrategy.SKIP,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    importer = WorkflowBundleImporter(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        payload=request.payload,
        strategy=strategy,
        workflow_repository=app_context.domain.workflow_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
        rule_repository=app_context.domain.workflow_rule_repository,
        document_type_repository=app_context.domain.document_type_repository,
        kb_document_repository=app_context.domain.kb_document_repository,
        dry_run=False,
    )
    report = await importer.execute()

    for rule_id in importer.rule_ids_to_recompile or []:
        background_tasks.add_task(
            schedule_and_run_compilation,
            rule_id,
            tenant.uuid,
            workflow_id,
            http_request.app.state.database_config,
            http_request.app.state.redis_client,
            http_request.app.state.event_publisher,
        )
    return ApiJSONResponse(content=report.to_dict(), status_code=status.HTTP_200_OK)
