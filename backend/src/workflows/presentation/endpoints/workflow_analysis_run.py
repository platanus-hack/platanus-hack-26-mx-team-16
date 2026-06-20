"""WorkflowAnalysisRun endpoints (renamed from analysis_run)."""

from __future__ import annotations

from fastapi import Depends, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import (
    EventPublisherDep,
    RedisClientDep,
    TemporalClientDep,
    get_app_context,
)
from src.common.infrastructure.dependencies.session import AuthenticatedUserDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.infrastructure.sse.streaming import stream_sse
from src.common.settings import settings
from src.workflows.application.analysis_runs.cancel import (
    CancelWorkflowAnalysisRun,
)
from src.workflows.application.analysis_runs.force_cancel import (
    ForceCancelWorkflowAnalysisRun,
)
from src.workflows.application.analysis_runs.getters import (
    GetWorkflowAnalysisRunDetail,
    ListWorkflowAnalysisRunsForCase,
)
from src.workflows.application.analysis_runs.starter import (
    StartWorkflowAnalysisRun,
)
from src.workflows.domain.events.workflow_analysis_run_event import (
    RUN_TERMINAL_EVENT_TYPES,
    channel_for_run,
)
from src.workflows.presentation.presenters.workflow_analysis_run import (
    WorkflowAnalysisRunDetailPresenter,
    WorkflowAnalysisRunPresenter,
)

from uuid import UUID

from fastapi import Request
from sse_starlette.sse import EventSourceResponse


async def create_workflow_analysis_run(
    workflow_id: UUID,
    case_id: UUID,
    user: AuthenticatedUserDep,
    temporal_client: TemporalClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    run = await StartWorkflowAnalysisRun(
        workflow_id=workflow_id,
        case_id=case_id,
        tenant_id=tenant.uuid,
        triggered_by=user.uuid,
        workflow_repository=app_context.domain.workflow_repository,
        case_repository=app_context.domain.workflow_case_repository,
        run_repository=app_context.domain.workflow_analysis_run_repository,
        temporal_client=temporal_client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowAnalysisRunPresenter(instance=run).to_dict,
        status_code=status.HTTP_202_ACCEPTED,
    )


async def list_workflow_analysis_runs(
    workflow_id: UUID,  # noqa: ARG001 — kept for URL nesting; ownership at case level
    case_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    runs = await ListWorkflowAnalysisRunsForCase(
        case_id=case_id,
        tenant_id=tenant.uuid,
        run_repository=app_context.domain.workflow_analysis_run_repository,
    ).execute()
    return ApiJSONResponse(
        content=[WorkflowAnalysisRunPresenter(instance=r).to_dict for r in runs],
        status_code=status.HTTP_200_OK,
    )


async def get_workflow_analysis_run(
    run_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    run, results = await GetWorkflowAnalysisRunDetail(
        run_id=run_id,
        tenant_id=tenant.uuid,
        run_repository=app_context.domain.workflow_analysis_run_repository,
        result_repository=app_context.domain.workflow_rule_result_repository,
    ).execute()
    # Resolve rule_id → name once per workflow so each result card can
    # surface the rule's human title (instead of the generic "Regla").
    rules = await app_context.domain.workflow_rule_repository.list_by_workflow(run.workflow_id, tenant.uuid)
    rule_names = {r.uuid: r.name for r in rules}
    return ApiJSONResponse(
        content=WorkflowAnalysisRunDetailPresenter(instance=run, results=results, rule_names=rule_names).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def cancel_workflow_analysis_run(
    run_id: UUID,
    user: AuthenticatedUserDep,
    temporal_client: TemporalClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    run = await CancelWorkflowAnalysisRun(
        run_id=run_id,
        tenant_id=tenant.uuid,
        canceled_by=user.uuid,
        run_repository=app_context.domain.workflow_analysis_run_repository,
        temporal_client=temporal_client,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowAnalysisRunPresenter(instance=run).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def force_cancel_workflow_analysis_run(
    run_id: UUID,
    user: AuthenticatedUserDep,
    temporal_client: TemporalClientDep,
    event_publisher: EventPublisherDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    run = await ForceCancelWorkflowAnalysisRun(
        run_id=run_id,
        tenant_id=tenant.uuid,
        canceled_by=user.uuid,
        run_repository=app_context.domain.workflow_analysis_run_repository,
        temporal_client=temporal_client,
        event_publisher=event_publisher,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowAnalysisRunPresenter(instance=run).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def stream_workflow_analysis_run_events(
    run_id: UUID,
    request: Request,
    redis_client: RedisClientDep,
) -> EventSourceResponse:
    return stream_sse(
        channel=channel_for_run(run_id),
        redis_client=redis_client,
        request=request,
        close_after=RUN_TERMINAL_EVENT_TYPES,
    )
