from datetime import datetime

from fastapi import Depends, Query, Security, status

from src.common.domain.entities.common.pagination import Page
from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.models.tenants.tenant_user import TenantUser
from src.common.domain.permissions.checker import check_tenant_permission
from src.common.domain.permissions.namespaces.workflow import WorkflowPermission
from src.common.infrastructure.dependencies.api_keys import get_admin_api_key
from src.common.infrastructure.dependencies.common import DomainContextDep, get_app_context
from src.common.infrastructure.dependencies.tenant import get_required_tenant, get_required_tenant_user
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.usage.application.use_cases.create_process_record import CreateProcessRecord
from src.usage.application.use_cases.get_process_records_summary import GetProcessRecordsSummary
from src.usage.application.use_cases.list_process_records import ListProcessRecords
from src.usage.presentation.presenters.process_record import ProcessRecordPresenter, UsageSummaryPresenter
from src.usage.presentation.schemas.process_record import CreateProcessRecordSchema


async def create_process_record(
    body: CreateProcessRecordSchema,
    domain_context: DomainContextDep,
    tenant: Tenant = Depends(get_required_tenant),
    _api_key: str = Security(get_admin_api_key),
) -> ApiJSONResponse:
    record = await CreateProcessRecord(
        tenant=tenant,
        workflow_id=body.workflow_id,
        object_key_digest=body.object_key_digest,
        page_count=body.page_count,
        analysis_run_id=body.analysis_run_id,
        process_record_repository=domain_context.process_record_repository,
    ).execute()
    return ApiJSONResponse(
        content=ProcessRecordPresenter(instance=record).to_dict,
        status_code=status.HTTP_201_CREATED,
    )


async def list_process_records(
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    tenant_user: TenantUser = Depends(get_required_tenant_user),
    from_dt: datetime | None = Query(default=None, alias="fromDt"),
    to_dt: datetime | None = Query(default=None, alias="toDt"),
    limit: int = Query(default=25, ge=1, le=200),
    cursor: str | None = Query(default=None),
) -> ApiJSONResponse:
    check_tenant_permission(tenant_user, permissions=[WorkflowPermission.view_usage])
    page = await ListProcessRecords(
        tenant_id=tenant.uuid,
        process_record_repository=app_context.domain.process_record_repository,
        from_dt=from_dt,
        to_dt=to_dt,
        limit=limit,
        cursor=cursor,
    ).execute()
    presented_page = Page(
        next_cursor=page.next_cursor,
        items=[ProcessRecordPresenter(instance=r).to_dict for r in (page.items or [])],
        limit=page.limit,
    )
    return ApiJSONResponse(
        content=presented_page,
        status_code=status.HTTP_200_OK,
    )


async def get_usage_summary(
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
    tenant_user: TenantUser = Depends(get_required_tenant_user),
) -> ApiJSONResponse:
    check_tenant_permission(tenant_user, permissions=[WorkflowPermission.view_usage])
    summary = await GetProcessRecordsSummary(
        tenant=tenant,
        process_record_repository=app_context.domain.process_record_repository,
    ).execute()
    return ApiJSONResponse(
        content=UsageSummaryPresenter(instance=summary).to_dict,
        status_code=status.HTTP_200_OK,
    )
