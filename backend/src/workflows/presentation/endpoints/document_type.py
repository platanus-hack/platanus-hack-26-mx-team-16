"""Tenant-scoped document type endpoints — UseCase + Presenter pattern."""

from uuid import UUID

from fastapi import BackgroundTasks, Depends, Request, status
from sse_starlette.sse import EventSourceResponse

from src.common.application.commands.document_types import (
    ExtractDocumentTypeSampleTextCommand,
    SuggestDocumentTypeFieldsCommand,
)
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.workflow import WorkflowPermission
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import RedisClientDep, get_app_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant, get_required_tenant_user
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.infrastructure.sse.streaming import stream_sse
from src.workflows.application.document_types.compilation_invalidator import (
    DocumentTypeCompilationInvalidator,
)
from src.workflows.application.document_types.deleter import DocumentTypeDeleter
from src.workflows.application.document_types.getter import DocumentTypeGetter
from src.workflows.application.document_types.tenant_lister import (
    DocumentTypeTenantLister,
)
from src.workflows.application.document_types.updater import DocumentTypeUpdater
from src.workflows.application.workflow_rules.compilation.background import (
    schedule_and_run_compilation,
)
from src.workflows.domain.events.document_type_event import (
    DOCTYPE_TERMINAL_EVENT_TYPES,
    channel_for_doctype,
)
from src.workflows.presentation.presenters.document_type import DocumentTypePresenter
from src.workflows.presentation.schemas.document_type import (
    SuggestDocumentTypeFieldsRequest,
    UpdateDocumentTypeRequest,
)


async def list_document_types(
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    document_types = await DocumentTypeTenantLister(
        tenant_id=tenant.uuid,
        document_type_repository=app_context.domain.document_type_repository,
    ).execute()
    return ApiJSONResponse(
        content=[DocumentTypePresenter(instance=dt).to_dict for dt in document_types],
        status_code=status.HTTP_200_OK,
    )


async def get_document_type(
    document_type_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.view])
    document_type = await DocumentTypeGetter(
        document_type_id=document_type_id,
        tenant_id=tenant.uuid,
        document_type_repository=app_context.domain.document_type_repository,
    ).execute()
    return ApiJSONResponse(
        content=DocumentTypePresenter(instance=document_type).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def update_document_type(
    document_type_id: UUID,
    request: UpdateDocumentTypeRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.update])
    outcome = await DocumentTypeUpdater(
        document_type_id=document_type_id,
        tenant_id=tenant.uuid,
        name=request.name,
        description=request.description,
        is_shareable=request.is_shareable,
        fields=request.fields,
        keywords=request.keywords,
        examples=request.examples,
        validation_rules=request.validation_rules,
        sample_file_id=request.sample_file_id,
        document_type_repository=app_context.domain.document_type_repository,
    ).execute()
    document_type = outcome.document_type

    # Nueva versión del contrato ⇒ las compilaciones de reglas que referencian
    # este doc type quedan STALE y se recompilan en background (mismo flujo
    # que una edición invalidante de la regla, ver compilation_invalidator).
    if outcome.created_new_version:
        invalidated = await DocumentTypeCompilationInvalidator(
            workflow_id=document_type.workflow_id,
            tenant_id=tenant.uuid,
            document_type_id=document_type.uuid,
            document_type_slug=document_type.slug,
            rule_repository=app_context.domain.workflow_rule_repository,
            compilation_repository=app_context.domain.workflow_rule_compilation_repository,
        ).execute()
        for rule in invalidated:
            background_tasks.add_task(
                schedule_and_run_compilation,
                rule.uuid,
                tenant.uuid,
                rule.workflow_id,
                http_request.app.state.database_config,
                http_request.app.state.redis_client,
                http_request.app.state.event_publisher,
            )

    if request.sample_file_id is not None:
        await app_context.bus.command_bus.dispatch(
            ExtractDocumentTypeSampleTextCommand(
                document_type_id=document_type_id,
                tenant_id=tenant.uuid,
            ),
            run_async=True,
        )

    return ApiJSONResponse(
        content=DocumentTypePresenter(instance=document_type).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def suggest_document_type_fields(
    document_type_id: UUID,
    request: SuggestDocumentTypeFieldsRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    # Validate ownership and clear stale fields synchronously so the frontend
    # can call loadDocType after 202 and immediately see an empty schema.
    await DocumentTypeUpdater(
        document_type_id=document_type_id,
        tenant_id=tenant.uuid,
        document_type_repository=app_context.domain.document_type_repository,
        clear_fields=True,
    ).execute()

    await app_context.bus.command_bus.dispatch(
        SuggestDocumentTypeFieldsCommand(
            document_type_id=document_type_id,
            tenant_id=tenant.uuid,
            prompt=request.prompt,
        ),
        run_async=True,
    )

    return ApiJSONResponse(content=None, status_code=status.HTTP_202_ACCEPTED)


async def stream_document_type_events(
    document_type_id: UUID,
    request: Request,
    redis_client: RedisClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> EventSourceResponse:
    await DocumentTypeGetter(
        document_type_id=document_type_id,
        tenant_id=tenant.uuid,
        document_type_repository=app_context.domain.document_type_repository,
    ).execute()

    return stream_sse(
        channel=channel_for_doctype(document_type_id),
        redis_client=redis_client,
        request=request,
        close_after=DOCTYPE_TERMINAL_EVENT_TYPES,
    )


async def delete_document_type(
    document_type_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    current_tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(current_tenant_user, permissions=[WorkflowPermission.delete])
    await DocumentTypeDeleter(
        document_type_id=document_type_id,
        tenant_id=tenant.uuid,
        document_type_repository=app_context.domain.document_type_repository,
    ).execute()
    return ApiJSONResponse(
        content={"status": "deleted"},
        status_code=status.HTTP_200_OK,
    )
