"""Extraction workflow CRUD endpoints — UseCase + Presenter pattern."""

from uuid import UUID

import yaml
from fastapi import BackgroundTasks, Depends, Query, Request, status
from yaml import YAMLError

from src.common.domain.exceptions.processing import InvalidWorkflowYamlError
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.workflow import WorkflowPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import get_app_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant, get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.workflows.application.workflow_rules.compilation.background import (
    schedule_and_run_compilation,
)
from src.workflows.application.workflows.capabilities_resolver import (
    WorkflowCapabilitiesResolver,
    capabilities_to_payload,
)
from src.workflows.application.workflows.creator import WorkflowCreator
from src.workflows.application.workflows.deleter import WorkflowDeleter
from src.workflows.application.workflows.getter import WorkflowGetter
from src.workflows.application.workflows.import_export.importer import (
    ImportConflictStrategy,
    WorkflowBundleImporter,
)
from src.workflows.application.workflows.lister import WorkflowsLister
from src.workflows.application.workflows.updater import WorkflowUpdater
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.presentation.presenters.workflow import WorkflowPresenter
from src.workflows.presentation.schemas.workflow_schemas import (
    CreateWorkflowFromYamlRequest,
    CreateWorkflowRequest,
    UpdateWorkflowRequest,
)


async def _present_workflow(workflow: Workflow, pipeline_repository: PipelineRepository) -> dict:
    """Presenta un workflow con sus capacidades derivadas del pipeline (E7 · F0)."""
    capabilities = await WorkflowCapabilitiesResolver(
        pipeline_repository=pipeline_repository
    ).for_workflow(workflow)
    return WorkflowPresenter(
        instance=workflow, capabilities=capabilities_to_payload(capabilities)
    ).to_dict


async def list_workflows(
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
    industry_id: UUID | None = Query(default=None, alias="industryId"),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    workflows = await WorkflowsLister(
        tenant_id=tenant.uuid,
        workflow_repository=app_context.domain.workflow_repository,
        industry_id=industry_id,
        member_repository=app_context.domain.workflow_member_repository,
        tenant_user=current_tenant_user,
    ).execute()
    capabilities = await WorkflowCapabilitiesResolver(
        pipeline_repository=app_context.domain.pipeline_repository
    ).for_workflows(workflows)
    return ApiJSONResponse(
        content=[
            WorkflowPresenter(
                instance=w, capabilities=capabilities_to_payload(capabilities[w.uuid])
            ).to_dict
            for w in workflows
        ],
        status_code=status.HTTP_200_OK,
    )


async def get_workflow(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    workflow = await WorkflowGetter(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        workflow_repository=app_context.domain.workflow_repository,
    ).execute()
    return ApiJSONResponse(
        content=await _present_workflow(workflow, app_context.domain.pipeline_repository),
        status_code=status.HTTP_200_OK,
    )


async def create_workflow(
    request: CreateWorkflowRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.create])
    workflow = await WorkflowCreator(
        tenant_id=tenant.uuid,
        name=request.name,
        template_slug=request.template_slug,
        industry_id=request.industry_id,
        selected_doc_types=request.selected_doc_types,
        kb_document_ids=request.kb_document_ids,
        per_doc_kb_ids=request.per_doc_kb_ids,
        structuring_model=request.structuring_model,
        llm_model=request.llm_model,
        created_by_id=current_tenant_user.user_id,
        workflow_repository=app_context.domain.workflow_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
    ).execute()
    return ApiJSONResponse(
        content=await _present_workflow(workflow, app_context.domain.pipeline_repository),
        status_code=status.HTTP_201_CREATED,
    )


async def create_workflow_from_yaml(
    request: CreateWorkflowFromYamlRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    """Crea un workflow desde una plantilla YAML (envelope de bundle).

    Se parsea ANTES de crear nada: un YAML inválido aborta sin dejar un workflow
    huérfano. El bundle se importa con OVERWRITE sobre el pipeline estándar recién
    sembrado, replicando el flujo «crear + importar» del catálogo de plantillas.
    """
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.create])

    try:
        envelope = yaml.safe_load(request.yaml)
    except YAMLError as exc:
        raise InvalidWorkflowYamlError(str(exc)) from exc
    if not isinstance(envelope, dict):
        detail = "root must be a mapping"
        raise InvalidWorkflowYamlError(detail)

    workflow = await WorkflowCreator(
        tenant_id=tenant.uuid,
        name=request.name,
        created_by_id=current_tenant_user.user_id,
        workflow_repository=app_context.domain.workflow_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
    ).execute()

    importer = WorkflowBundleImporter(
        workflow_id=workflow.uuid,
        tenant_id=tenant.uuid,
        payload=envelope,
        strategy=ImportConflictStrategy.OVERWRITE,
        workflow_repository=app_context.domain.workflow_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
        rule_repository=app_context.domain.workflow_rule_repository,
        document_type_repository=app_context.domain.document_type_repository,
        kb_document_repository=app_context.domain.kb_document_repository,
        dry_run=False,
    )
    await importer.execute()

    for rule_id in importer.rule_ids_to_recompile or []:
        background_tasks.add_task(
            schedule_and_run_compilation,
            rule_id,
            tenant.uuid,
            workflow.uuid,
            http_request.app.state.database_config,
            http_request.app.state.redis_client,
            http_request.app.state.event_publisher,
        )

    refreshed = await WorkflowGetter(
        workflow_id=workflow.uuid,
        tenant_id=tenant.uuid,
        workflow_repository=app_context.domain.workflow_repository,
    ).execute()
    return ApiJSONResponse(
        content=await _present_workflow(refreshed, app_context.domain.pipeline_repository),
        status_code=status.HTTP_201_CREATED,
    )


async def update_workflow(
    workflow_id: UUID,
    request: UpdateWorkflowRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    workflow = await WorkflowUpdater(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        workflow_repository=app_context.domain.workflow_repository,
        name=request.name,
        selected_doc_types=request.selected_doc_types,
        kb_document_ids=request.kb_document_ids,
        per_doc_kb_ids=request.per_doc_kb_ids,
        structuring_model=request.structuring_model,
        llm_model=request.llm_model,
        webhook_url=request.webhook_url,
        webhook_enabled=request.webhook_enabled,
        webhook_events=request.webhook_events,
        case_noun=request.case_noun,
    ).execute()
    return ApiJSONResponse(
        content=await _present_workflow(workflow, app_context.domain.pipeline_repository),
        status_code=status.HTTP_200_OK,
    )


async def delete_workflow(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.delete])
    await WorkflowDeleter(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        workflow_repository=app_context.domain.workflow_repository,
    ).execute()
    return ApiJSONResponse(
        content={"status": "deleted"},
        status_code=status.HTTP_200_OK,
    )
