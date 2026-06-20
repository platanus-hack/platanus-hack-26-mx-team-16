"""Public ingest endpoint — ``POST /v1/ingest/{token}`` (F8 · W2 · E4).

No JWT: the Source's own ``auth_mode`` (api_key here; HMAC for non-multipart) is
the credential. Resolves the route token, authenticates, optionally resolves the
case reference (spec source_webhooks §7.3: ``caseId`` | ``caseName`` form
fields — find-or-create), streams the upload to S3, opens a processing-job row,
and dispatches the generic ``PipelineInterpreterWorkflow``.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import Form, Security, UploadFile, status
from fastapi.security.api_key import APIKeyHeader

from src.common.database.config import get_database_config
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.common.infrastructure.dependencies.common import AsyncSessionDep, TemporalClientDep
from src.common.infrastructure.responses.api_json import ApiJSONResponse
from src.common.settings import settings
from src.connections.domain.exceptions import (
    IngestCaseNotFoundError,
    SourceAuthFailedError,
    SourceNotFoundError,
)
from src.connections.domain.services.source_auth import verify_source_auth
from src.connections.infrastructure.repositories.sql_workflow_source import (
    SQLWorkflowSourceRepository,
)
from src.storage.application.use_cases.upload_file import UploadFileUseCase
from src.storage.infrastructure.repositories.s3_file_repository import S3FileRepository
from src.workflows.application.sources.ingest import IngestViaSource, ResolveIngestCase
from src.workflows.infrastructure.repositories.sql_document_type import (
    SQLDocumentTypeRepository,
)
from src.workflows.infrastructure.repositories.sql_pipeline import SQLPipelineRepository
from src.workflows.infrastructure.repositories.sql_workflow import SQLWorkflowRepository
from src.workflows.infrastructure.repositories.sql_workflow_case import (
    SQLWorkflowCaseRepository,
)
from src.workflows.infrastructure.repositories.sql_workflow_processing_job import (
    SQLWorkflowProcessingJobRepository,
)
from src.workflows.infrastructure.services.webhooks.case_event_dispatcher import (
    CaseEventDispatcher,
)

_ingest_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False)


def _parse_case_id(raw: str | None) -> UUID | None:
    if raw is None or not raw.strip():
        return None
    try:
        return UUID(raw.strip())
    except ValueError as exc:
        raise IngestCaseNotFoundError(raw) from exc


async def ingest_via_source(
    token: str,
    file: UploadFile,
    session: AsyncSessionDep,
    temporal_client: TemporalClientDep,
    api_key: str = Security(_ingest_key_header),
    # Spec source_webhooks §7.3 — form fields, opcionales, solo ANALYSIS.
    case_id: str | None = Form(default=None, alias="caseId"),
    case_name: str | None = Form(default=None, alias="caseName", max_length=255),
) -> ApiJSONResponse:
    source_repo = SQLWorkflowSourceRepository(session)
    source = await source_repo.find_by_route_token(token)
    if source is None or not source.enabled:
        raise SourceNotFoundError(token)
    if not verify_source_auth(source, api_key=api_key):
        raise SourceAuthFailedError

    # E4: vínculo a caso ANTES de subir (validación previa, spec §7.2) —
    # find-or-create por caseName/external_ref, case.created solo en creación
    # real, CASE# idempotente. Sin referencia ⇒ set anónimo (intacto).
    case_result = await ResolveIngestCase(
        tenant_id=source.tenant_id,
        workflow_id=source.workflow_id,
        case_id=_parse_case_id(case_id),
        case_name=(case_name or "").strip() or None,
        workflow_repository=SQLWorkflowRepository(session),
        case_repository=SQLWorkflowCaseRepository(session),
        pipeline_repository=SQLPipelineRepository(session),
        temporal_client=temporal_client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        case_event_dispatcher=CaseEventDispatcher(
            session_maker=get_database_config().session_maker
        ),
    ).execute()
    case = case_result.case

    uploaded = await UploadFileUseCase(
        tenant_id=source.tenant_id,
        file=file,
        file_repository=S3FileRepository(session),
    ).execute()

    job_id = f"SRC#{source.route_token}_FILE#{uploaded.uuid.hex[:12]}"
    ds_repo = SQLWorkflowProcessingJobRepository(session)
    processing_job = await ds_repo.find_by_temporal_workflow_id(job_id)
    if processing_job is None:
        processing_job = await ds_repo.create(
            WorkflowProcessingJob(
                uuid=uuid4(),
                temporal_workflow_id=job_id,
                tenant_id=source.tenant_id,
                workflow_id=source.workflow_id,
                workflow_case_id=case.uuid if case is not None else None,
                file_id=uploaded.uuid,
            )
        )
    await session.commit()

    result_job_id = await IngestViaSource(
        route_token=token,
        object_key=uploaded.s3_key,
        file_name=uploaded.file_name,
        source_repository=source_repo,
        pipeline_repository=SQLPipelineRepository(session),
        document_type_repository=SQLDocumentTypeRepository(session),
        temporal_client=temporal_client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        file_id=uploaded.uuid,
        processing_job_uuid=processing_job.uuid,
        case_id=case.uuid if case is not None else None,
        api_key=api_key,
    ).execute()

    return ApiJSONResponse(
        content={
            "job_id": result_job_id,
            "processing_job_id": str(processing_job.uuid),
            # Spec §5.7: envelope con la referencia del caso ({id, name} | null).
            "case": ({"id": str(case.uuid), "name": case.name} if case is not None else None),
        },
        status_code=status.HTTP_202_ACCEPTED,
    )
