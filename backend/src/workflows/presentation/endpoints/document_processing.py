from uuid import UUID

from fastapi import Depends, status

from src.common.domain.models.tenants.tenant import Tenant
from src.common.domain.enums.workflows import WorkflowDocumentSource
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
from src.workflows.application.workflow_documents.by_id_getter import (
    WorkflowDocumentByIdGetter,
)
from src.workflows.presentation.presenters.workflow_document import WorkflowDocumentPresenter
from src.workflows.presentation.presenters.workflow_processing_job import (
    WorkflowProcessingJobPresenter,
)
from src.common.domain.exceptions.processing import DocumentNotFoundError
from src.workflows.application.document_processing.status_getter import ExtractionStatusGetter
from src.workflows.application.workflow_documents.getter import DocumentGetter
from src.workflows.application.document_processing.extraction_starter import (
    StartCaseDocumentExtraction,
)


async def start_case_document_extraction(
    workflow_id: UUID,
    case_id: UUID,
    document_id: UUID,
    temporal_client: TemporalClientDep,
    session: AsyncSessionDep,
    user: AuthenticatedUserDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    # Re-extraction on a BULK document deletes all siblings (same file_id) and
    # re-runs the whole file through Temporal. SINGLE docs keep the in-place
    # update flow (StartCaseDocumentExtraction).
    doc = await app_context.domain.document_repository.find_by_id(document_id, tenant.uuid)
    if doc is None:
        raise DocumentNotFoundError(str(document_id))

    # E3: los documentos virtuales (datos inyectados / resultados de tools) no
    # tienen archivo — re-extraerlos no significa nada; re-envía los datos.
    if doc.source in (WorkflowDocumentSource.EXTERNAL_DATA, WorkflowDocumentSource.TOOL):
        return ApiJSONResponse(
            content={
                "error": "document.virtual_not_extractable",
                "detail": "virtual documents (external data / tool results) cannot be re-extracted; submit new data instead",
            },
            status_code=status.HTTP_409_CONFLICT,
        )

    if doc.source == WorkflowDocumentSource.BULK and doc.file_id is not None:
        repo = app_context.domain.document_repository
        siblings = await repo.list_by_case_and_file(case_id, doc.file_id, tenant.uuid)
        for sibling in siblings:
            await repo.delete(sibling.uuid, tenant.uuid)
        await session.commit()

        processing_job = await WorkflowProcessingJobDispatcher(
            tenant_id=tenant.uuid,
            workflow_id=workflow_id,
            file_id=doc.file_id,
            workflow_case_id=case_id,
            session=session,
            temporal_client=temporal_client,
            processing_job_repository=app_context.domain.processing_job_repository,
            workflow_repository=app_context.domain.workflow_repository,
            workflow_case_repository=app_context.domain.workflow_case_repository,
            document_type_repository=app_context.domain.document_type_repository,
            file_repository=app_context.domain.file_repository,
            pipeline_repository=app_context.domain.pipeline_repository,
            task_queue=settings.TEMPORAL_TASK_QUEUE,
            force_restart=True,
            created_by_id=user.uuid,
        ).execute()
        return ApiJSONResponse(
            content=WorkflowProcessingJobPresenter(instance=processing_job).to_dict,
            status_code=status.HTTP_202_ACCEPTED,
        )

    result = await StartCaseDocumentExtraction(
        workflow_id=workflow_id,
        case_id=case_id,
        document_id=document_id,
        tenant_id=tenant.uuid,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        temporal_client=temporal_client,
        document_repository=app_context.domain.document_repository,
        file_repository=app_context.domain.file_repository,
        document_type_repository=app_context.domain.document_type_repository,
        workflow_repository=app_context.domain.workflow_repository,
        pipeline_repository=app_context.domain.pipeline_repository,
    ).execute()

    return ApiJSONResponse(
        content=result,
        status_code=status.HTTP_202_ACCEPTED,
    )


async def get_workflow_document(
    document_id: UUID,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    document = await WorkflowDocumentByIdGetter(
        document_id=document_id,
        tenant_id=tenant.uuid,
        document_repository=app_context.domain.document_repository,
    ).execute()
    return ApiJSONResponse(
        content=WorkflowDocumentPresenter(instance=document).to_dict,
        status_code=status.HTTP_200_OK,
    )


async def get_case_document_extraction_status(
    workflow_id: UUID,  # noqa: ARG001 — kept for URL symmetry, not used in lookup
    case_id: UUID,
    document_id: UUID,
    temporal_client: TemporalClientDep,
    app_context: AppContext = Depends(get_app_context),
    tenant: Tenant = Depends(get_required_tenant),
) -> ApiJSONResponse:
    result = await ExtractionStatusGetter(
        case_id=case_id,
        document_id=document_id,
        tenant_id=tenant.uuid,
        temporal_client=temporal_client,
    ).execute()
    return ApiJSONResponse(content=result, status_code=status.HTTP_200_OK)
