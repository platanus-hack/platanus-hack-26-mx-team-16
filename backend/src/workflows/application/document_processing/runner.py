"""Use case that waits for a Temporal workflow result and reports back the
documents the worker already persisted.

The Temporal worker is the single writer of `workflow_documents` for a document set:
- `persist_classified_documents` activity creates the rows right after
  `classify_pages`.
- `mark_document_status` activity updates each row at the end of
  `extract_fields` / `validate_extraction` (extraction, validation,
  status, extraction_pages).

This use case runs in the FastAPI process. It only:
1) Claims the `workflow_processing_jobs` row atomically (so two replicas don't fight).
2) Waits for the workflow result via gRPC long-poll (`handle.result()`).
3) Validates the global Lambda statuses.
4) Reads the rows the worker already wrote, marks the document set done, and
   returns them to the caller.
"""

from dataclasses import dataclass
from datetime import timedelta

from temporalio.client import Client as TemporalClient

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.document_processing import (
    DocumentProcessingOutput,
)
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository

logger = get_logger(__name__)


@dataclass
class RunAndPersistDocumentProcessing:
    """Espera el resultado del workflow Temporal (gRPC long-poll), marca el
    `workflow_processing_job` como done y devuelve los `WorkflowDocument` que el
    worker ya persistió. NO arranca el workflow ni crea filas — eso lo
    hacen el endpoint y las activities del worker."""

    processing_job: WorkflowProcessingJob
    extraction_timeout_seconds: int
    temporal_client: TemporalClient
    processing_job_repository: WorkflowProcessingJobRepository
    document_repository: WorkflowDocumentRepository

    async def execute(self) -> list[WorkflowDocument]:
        # 1) Claim atómico — si otro worker ya lo agarró, abortamos
        claimed = await self.processing_job_repository.claim(self.processing_job.uuid)
        if claimed is None:
            logger.info(
                f"workflow_processing_job.skipped_already_claimed temporal_workflow_id={self.processing_job.temporal_workflow_id}"
            )
            return []

        try:
            # 2) gRPC long-poll: la conexión TCP queda dormida hasta que el workflow completa
            handle = self.temporal_client.get_workflow_handle(self.processing_job.temporal_workflow_id)
            raw = await handle.result(
                rpc_timeout=timedelta(seconds=self.extraction_timeout_seconds),
            )
            output = DocumentProcessingOutput.model_validate(raw)

            # 3) Validar status global
            ef_status = (output.extract_fields or {}).get("status")
            vx_status = (output.validate_extraction or {}).get("status")
            if ef_status == "error":
                raise RuntimeError(f"extract_fields failed: {(output.extract_fields or {}).get('message')}")

            # 4) Leer las filas que el worker ya persistió/finalizó
            documents = await self.document_repository.list_by_processing_job(self.processing_job.uuid)

            # 5) Marcar done con un resumen
            summary = {
                "documents_created": len(documents),
                "extract_fields_status": ef_status,
                "validate_extraction_status": vx_status,
                "extract_fields_errors": (output.extract_fields or {}).get("errors") or [],
                "validate_extraction_errors": (output.validate_extraction or {}).get("errors") or [],
            }
            await self.processing_job_repository.mark_done(self.processing_job.uuid, summary)
            return documents

        except Exception as exc:
            logger.exception(f"workflow_processing_job.failed temporal_workflow_id={self.processing_job.temporal_workflow_id}")
            await self.processing_job_repository.mark_failed(self.processing_job.uuid, str(exc))
            raise
