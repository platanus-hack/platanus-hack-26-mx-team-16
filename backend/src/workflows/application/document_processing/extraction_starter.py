from dataclasses import dataclass
from uuid import UUID

from temporalio.client import Client as TemporalClient
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RPCError, RPCStatusCode

from src.common.domain.entities.workflows.document_processing import DocumentProcessingInput
from src.common.domain.entities.workflows.pipeline_run import PipelineRunInput
from src.common.domain.interfaces.use_case import UseCase
from src.workflows.application.document_types.lister import (
    DocumentTypeLister,
)
from src.common.domain.models.processing.document_type import DocumentType
from src.workflows.application.pipelines.resolver import resolve_workflow_pipeline
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.storage.domain.repositories.file_repository import FileRepository
from src.workflows.application.workflow_documents.getter import DocumentGetter
from src.workflows.presentation.workflows.pipeline_interpreter import (
    PipelineInterpreterWorkflow,
)


def _doctype_to_dict(dt: DocumentType) -> dict:
    schema = dt.fields or {}
    fields = schema.get("fields") if isinstance(schema, dict) else None
    return {
        "uuid": str(dt.uuid),
        "name": dt.name,
        # Sellado D6': slug + versión CURRENT del contrato al despachar.
        "slug": dt.slug,
        "description": dt.description or "",
        "fields": fields if fields is not None else schema,
        "validation_rules": dt.validation_rules or [],
        "schema_version": dt.current_version,
    }


@dataclass
class StartCaseDocumentExtraction(UseCase):
    """Start the Temporal workflow for a single case document (SINGLE source).

    Persistence of the resulting extraction onto the WorkflowDocument row is
    handled by a separate layer (polled via GetExtractionStatus or a dedicated
    persistence use case that consumes DocumentProcessingOutput).
    """

    workflow_id: UUID
    case_id: UUID
    document_id: UUID
    tenant_id: UUID
    task_queue: str
    temporal_client: TemporalClient
    document_repository: WorkflowDocumentRepository
    file_repository: FileRepository
    document_type_repository: DocumentTypeRepository
    workflow_repository: WorkflowRepository
    pipeline_repository: PipelineRepository

    async def execute(self) -> dict:
        workflow_doc = await DocumentGetter(
            document_id=self.document_id,
            tenant_id=self.tenant_id,
            document_repository=self.document_repository,
            file_repository=self.file_repository,
        ).execute()

        doctypes = await DocumentTypeLister(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            document_type_repository=self.document_type_repository,
        ).execute()

        resolved = await resolve_workflow_pipeline(
            tenant_id=self.tenant_id,
            pipeline_repository=self.pipeline_repository,
            workflow_id=self.workflow_id,
        )

        job_id = f"case:{self.case_id.hex}_{self.document_id.hex}"
        # Standalone, status-poll-only flow: this use case does NOT create a
        # workflow_processing_job row, so we can't drive the live-feedback channel.
        # Set persist=False explicitly so the workflow doesn't even attempt
        # the SSE/PG checkpoints (they'd be silently no-op'd anyway because
        # case_id/processing_job_uuid are not provided here).
        workflow_input = PipelineRunInput(
            pipeline_id=resolved.pipeline_id,
            version=resolved.version,
            document=DocumentProcessingInput(
                object_key=workflow_doc.object_key,
                document_types=[_doctype_to_dict(dt) for dt in doctypes],
                job_id=job_id,
                persist=False,
            ),
        )

        try:
            handle = await self.temporal_client.start_workflow(
                PipelineInterpreterWorkflow.run,
                workflow_input,
                id=job_id,
                task_queue=self.task_queue,
            )
            status = "started"
        except WorkflowAlreadyStartedError:
            handle = self.temporal_client.get_workflow_handle(job_id)
            status = "already_running"
        except RPCError as err:
            if err.status == RPCStatusCode.ALREADY_EXISTS:
                handle = self.temporal_client.get_workflow_handle(job_id)
                status = "already_running"
            else:
                raise

        return {"workflowId": handle.id, "jobId": job_id, "status": status}
