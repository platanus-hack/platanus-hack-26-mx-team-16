"""Endpoints for the workflow-analysis-run summary aggregate."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Request, status
from sse_starlette.sse import EventSourceResponse

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import (
    RedisClientDep,
    get_app_context,
)
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.infrastructure.sse.streaming import stream_sse
from src.workflows.application.analysis_run_summary.resynthesizer import ResynthesizeSummary
from src.workflows.application.analysis_run_summary.summary_getter import GetRunSummary
from src.workflows.application.analysis_run_summary.update_workflow_synthesis_config import (
    UpdateWorkflowSynthesisConfig,
)
from src.workflows.domain.events.workflow_analysis_run_event import channel_for_run
from src.workflows.domain.run_summary.events import SUMMARY_TERMINAL_EVENT_TYPES
from src.workflows.infrastructure.services.rules.bootstrap import (
    build_synthesizer_agent,
)
from src.workflows.presentation.presenters.analysis_run_summary import (
    WorkflowAnalysisRunSummaryPresenter,
)
from src.workflows.application.workflows.capabilities_resolver import (
    WorkflowCapabilitiesResolver,
    capabilities_to_payload,
)
from src.workflows.presentation.presenters.workflow import WorkflowPresenter
from src.workflows.presentation.schemas.run_summary import (
    UpdateWorkflowOutputSchemaRequest,
)


async def get_run_summary(
    run_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    summary = await GetRunSummary(
        run_id=run_id,
        tenant_id=tenant.uuid,
        summary_repository=app_context.domain.run_summary_repository,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowAnalysisRunSummaryPresenter(instance=summary).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def resynthesize_run_summary(
    run_id: UUID,
    force: bool = False,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    summary = await ResynthesizeSummary(
        run_id=run_id,
        tenant_id=tenant.uuid,
        workflow_repository=app_context.domain.workflow_repository,
        run_repository=app_context.domain.workflow_analysis_run_repository,
        result_repository=app_context.domain.workflow_rule_result_repository,
        summary_repository=app_context.domain.run_summary_repository,
        agent=build_synthesizer_agent(),
        tenant=tenant,
        force=force,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowAnalysisRunSummaryPresenter(instance=summary).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def stream_run_summary_events(
    run_id: UUID,
    request: Request,
    redis_client: RedisClientDep,
) -> EventSourceResponse:
    return stream_sse(
        channel=channel_for_run(run_id),
        redis_client=redis_client,
        request=request,
        close_after=SUMMARY_TERMINAL_EVENT_TYPES,
    )


async def update_workflow_output_schema(
    workflow_id: UUID,
    request: UpdateWorkflowOutputSchemaRequest,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    workflow = await UpdateWorkflowSynthesisConfig(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        output_schema=request.output_schema,
        synthesis_template=request.synthesis_template,
        synthesis_enabled=request.synthesis_enabled,
        workflow_repository=app_context.domain.workflow_repository,
    ).execute()
    capabilities = await WorkflowCapabilitiesResolver(
        pipeline_repository=app_context.domain.pipeline_repository
    ).for_workflow(workflow)
    return ApiJSONResponse(
        content=WorkflowPresenter(
            instance=workflow, capabilities=capabilities_to_payload(capabilities)
        ).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def get_workflow_output_schema(
    workflow_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    workflow = await app_context.domain.workflow_repository.find_by_id(workflow_id, tenant.uuid)
    if workflow is None:
        raise WorkflowNotFoundError(str(workflow_id))
    return ApiJSONResponse(
        content={
            "output_schema": workflow.output_schema,
            "synthesis_template": workflow.synthesis_template,
            "synthesis_enabled": workflow.synthesis_enabled,
        },
        status_code=status.HTTP_200_OK,
    )
