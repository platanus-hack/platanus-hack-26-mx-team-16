"""WorkflowProcessingJob CRUD endpoints — UseCase + Presenter pattern.

`POST /v1/workflows/{workflow_id}/jobs` creates (or reuses) a
`workflow_processing_jobs` row and starts the Temporal
`ProcessingJobProcessingWorkflow`. STANDARD workflows omit `workflowCaseId`;
ANALYSIS workflows must provide it.

`GET /v1/workflows/{workflow_id}/jobs` returns every set for the
workflow (newest first), each enriched with the source file name and the
list of WorkflowDocuments persisted under it.

`GET /v1/workflow-processing-jobs/{processing_job_id}` returns a single set.

`DELETE /v1/workflows/{workflow_id}/jobs/{processing_job_id}` removes
the row; child WorkflowDocuments stay (FK is ON DELETE SET NULL).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends, Query, status

from src.common.domain.entities.common.pagination import Page
from src.common.domain.enums.workflows import (
    WorkflowProcessingJobStatus,
    WorkflowProcessingJobTrigger,
)
from src.common.domain.models.tenants.tenant import Tenant
from src.common.infrastructure.context_builder import AppContext
from src.common.infrastructure.dependencies.common import (
    AsyncSessionDep,
    TemporalClientDep,
    get_app_context,
)
from src.common.infrastructure.dependencies.session import AuthenticatedUserDep
from src.common.infrastructure.dependencies.tenant import get_required_tenant
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.settings import settings
from src.workflows.application.processing_jobs.dispatcher import (
    WorkflowProcessingJobDispatcher,
)
from src.workflows.application.processing_jobs.deleter import (
    WorkflowProcessingJobDeleter,
)
from src.workflows.application.processing_jobs.getter import (
    WorkflowProcessingJobGetter,
)
from src.workflows.application.processing_jobs.lister import (
    WorkflowProcessingJobLister,
)
from src.workflows.application.processing_jobs.phase_execution_lister import (
    WorkflowPhaseExecutionLister,
)
from src.workflows.application.processing_jobs.re_extractor import (
    CaseFieldReExtractionStarter,
)
from src.workflows.domain.filters.workflow_processing_job import WorkflowProcessingJobFilters
from src.workflows.presentation.presenters.workflow_phase_execution import (
    WorkflowPhaseExecutionPresenter,
)
from src.workflows.presentation.presenters.workflow_processing_job import (
    WorkflowProcessingJobPresenter,
)
from src.workflows.presentation.schemas.workflow_processing_job import (
    DispatchWorkflowProcessingJobRequest,
)


async def create_processing_job(
    workflow_id: UUID,
    request: DispatchWorkflowProcessingJobRequest,
    temporal_client: TemporalClientDep,
    session: AsyncSessionDep,
    user: AuthenticatedUserDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    processing_job = await WorkflowProcessingJobDispatcher(
        tenant_id=tenant.uuid,
        workflow_id=workflow_id,
        file_id=request.file_id,
        workflow_case_id=request.workflow_case_id,
        session=session,
        temporal_client=temporal_client,
        processing_job_repository=app_context.domain.processing_job_repository,
        workflow_repository=app_context.domain.workflow_repository,
        workflow_case_repository=app_context.domain.workflow_case_repository,
        document_type_repository=app_context.domain.document_type_repository,
        file_repository=app_context.domain.file_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        created_by_id=user.uuid,
    ).execute()

    return ApiJSONResponse(
        content=WorkflowProcessingJobPresenter(instance=processing_job).to_dict,
        status_code=status.HTTP_202_ACCEPTED,
    )


async def list_processing_jobs(
    workflow_id: UUID,
    filters: WorkflowProcessingJobFilters = Depends(),
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    page = await WorkflowProcessingJobLister(
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        filters=filters,
        processing_job_repository=app_context.domain.processing_job_repository,
        document_repository=app_context.domain.document_repository,
    ).execute()
    presented_page = Page(
        next_cursor=page.next_cursor,
        items=[
            WorkflowProcessingJobPresenter(
                instance=item.processing_job,
                file_name=item.file_name,
                documents=item.documents,
            ).to_dict
            for item in page.items or []
        ],
        limit=page.limit,
    )

    return ApiJSONResponse(content=presented_page, status_code=status.HTTP_200_OK)


async def get_processing_job(
    processing_job_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    processing_job = await WorkflowProcessingJobGetter(
        processing_job_id=processing_job_id,
        tenant_id=tenant.uuid,
        processing_job_repository=app_context.domain.processing_job_repository,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowProcessingJobPresenter(instance=processing_job).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def get_processing_job_phases(
    workflow_id: UUID,
    processing_job_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    """Per-phase execution timeline of a run (the "Ejecuciones" split detail).

    Ordered by recipe ``seq``; each row carries status, timing, the data the
    phase produced (``output_snapshot``) and any error.
    """
    phases = await WorkflowPhaseExecutionLister(
        processing_job_id=processing_job_id,
        workflow_id=workflow_id,
        tenant_id=tenant.uuid,
        processing_job_repository=app_context.domain.processing_job_repository,
        phase_execution_repository=app_context.domain.phase_execution_repository,
    ).execute()
    return ApiJSONResponse(
        content=[WorkflowPhaseExecutionPresenter(instance=phase).to_dict for phase in phases],
        status_code=status.HTTP_200_OK,
    )


async def delete_processing_job(
    workflow_id: UUID,  # noqa: ARG001 — kept for URL symmetry
    processing_job_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    await WorkflowProcessingJobDeleter(
        processing_job_id=processing_job_id,
        tenant_id=tenant.uuid,
        processing_job_repository=app_context.domain.processing_job_repository,
    ).execute()
    return ApiJSONResponse(
        content={"status": "deleted"},
        status_code=status.HTTP_200_OK,
    )


async def retry_processing_job(
    workflow_id: UUID,
    processing_job_id: UUID,
    temporal_client: TemporalClientDep,
    session: AsyncSessionDep,
    user: AuthenticatedUserDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    """Re-dispatch de un job FAILED (Re-IA 2026-06 · «Reintentar» en Actividad).

    Wrapper fino sobre el dispatcher: este ya upserta por
    ``temporal_workflow_id`` y FAILED es el único estado que permite
    re-dispatch implícito (``is_idempotent_skip``). Guard de tenant/workflow
    aquí; guard de estado explícito para que un doble clic no haga nada raro.
    """
    repo = app_context.domain.processing_job_repository
    job = await repo.find_by_uuid(processing_job_id)
    if job is None or job.tenant_id != tenant.uuid or job.workflow_id != workflow_id:
        return ApiJSONResponse(
            content={"error": "processing_job.not_found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )
    if job.status is not WorkflowProcessingJobStatus.FAILED:
        return ApiJSONResponse(
            content={
                "error": "processing_job.not_failed",
                "detail": "only FAILED jobs can be retried",
            },
            status_code=status.HTTP_409_CONFLICT,
        )

    processing_job = await WorkflowProcessingJobDispatcher(
        tenant_id=tenant.uuid,
        workflow_id=workflow_id,
        file_id=job.file_id,
        workflow_case_id=job.workflow_case_id,
        session=session,
        temporal_client=temporal_client,
        processing_job_repository=repo,
        workflow_repository=app_context.domain.workflow_repository,
        workflow_case_repository=app_context.domain.workflow_case_repository,
        document_type_repository=app_context.domain.document_type_repository,
        file_repository=app_context.domain.file_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        created_by_id=user.uuid,
        trigger=WorkflowProcessingJobTrigger.RETRY,
    ).execute()

    return ApiJSONResponse(
        content=WorkflowProcessingJobPresenter(instance=processing_job).to_dict,
        status_code=status.HTTP_202_ACCEPTED,
    )


async def re_extract_case_processing_jobs(
    workflow_id: UUID,
    case_id: UUID,
    temporal_client: TemporalClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    """Dispatch un run extract-only del intérprete por cada set del caso (E1).

    Refuses if any set is in flight or any analysis run is active. The
    response lists the dispatched Temporal workflow ids so the client can
    correlate them with the SSE stream if needed.
    """
    result = await CaseFieldReExtractionStarter(
        tenant_id=tenant.uuid,
        workflow_id=workflow_id,
        case_id=case_id,
        temporal_client=temporal_client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflow_repository=app_context.domain.workflow_repository,
        workflow_case_repository=app_context.domain.workflow_case_repository,
        processing_job_repository=app_context.domain.processing_job_repository,
        document_repository=app_context.domain.document_repository,
        document_type_repository=app_context.domain.document_type_repository,
        analysis_run_repository=app_context.domain.workflow_analysis_run_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
    ).execute()

    return ApiJSONResponse(
        content=result,
        status_code=status.HTTP_202_ACCEPTED,
    )
