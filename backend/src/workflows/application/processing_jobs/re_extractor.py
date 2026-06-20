"""Re-run extract_fields + validate_extraction on every set in a case.

Companion to ``WorkflowProcessingJobDispatcher`` (which runs the full
OCR → classify → persist → extract → validate pipeline). This use case
is invoked by the **Extraer Campos** action on the case-detail screen
and only refreshes the LLM-driven steps, leaving the persisted document
rows in place. One Temporal workflow is dispatched per
``WorkflowProcessingJob`` in the case.

Guards (mirrors ``AnalysisRunStarter._require_*`` helpers so the UI
button can rely on the same shape of error):

1. The case must exist within the workflow + tenant.
2. The case must contain at least one document set.
3. No set may be in flight (RUNNING / PROCESSING / PENDING).
4. No analysis run may be active (RUNNING / CANCELING) — otherwise the
   user would be re-extracting fields under an analysis already in
   progress over the previous extraction shape.
5. Every set must have a stored ``classified_pages`` S3 key (i.e. it
   reached classify_pages on its original run). Sets that never
   classified can't be re-extracted without redoing OCR.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from temporalio.client import Client as TemporalClient
from temporalio.exceptions import WorkflowAlreadyStartedError

from src.common.application.logging import get_logger
from src.common.domain.entities.workflows.document_processing import (
    DocumentProcessingInput,
    WorkflowDocumentRef,
)
from src.common.domain.entities.workflows.pipeline_run import PipelineRunInput
from src.common.domain.exceptions._base import DomainError
from src.common.domain.exceptions.processing import (
    AnalysisAlreadyRunningError,
    CaseNotFoundError,
    ExtractionInProgressError,
    NoDocumentsToAnalyzeError,
    WorkflowNotFoundError,
    WorkflowPipelineNotConfiguredError,
)
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob
from src.workflows.application.document_processing.input_builder import (
    doctype_to_temporal_dict,
)
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)
from src.workflows.presentation.workflows.pipeline_interpreter import (
    PipelineInterpreterWorkflow,
)

logger = get_logger(__name__)


class ClassifiedPagesMissingError(DomainError):
    def __init__(self, set_id: str):
        super().__init__(
            code="processing.ClassifiedPagesMissing",
            message=(
                f"Document set {set_id} has no classified_pages key — "
                "the original run must classify before re-extracting."
            ),
            status_code=409,
        )


@dataclass
class CaseFieldReExtractionStarter(UseCase):
    """Validates the case state and dispatches one Temporal workflow per set."""

    tenant_id: UUID
    workflow_id: UUID
    case_id: UUID

    temporal_client: TemporalClient
    task_queue: str

    workflow_repository: WorkflowRepository
    workflow_case_repository: WorkflowCaseRepository
    processing_job_repository: WorkflowProcessingJobRepository
    document_repository: WorkflowDocumentRepository
    document_type_repository: DocumentTypeRepository
    analysis_run_repository: WorkflowAnalysisRunRepository
    pipeline_repository: PipelineRepository

    async def execute(self) -> dict:
        await self._require_workflow()
        await self._require_case()
        await self._require_no_active_analysis_run()
        sets = await self._require_sets_in_case()
        self._require_no_in_flight(sets)
        recipe = await self._require_re_extract_recipe()

        documents_by_set = await self._load_documents(sets)
        # Re-extracción usa el contrato CURRENT (status quo deliberado, D6'):
        # se relee cada doc type fresco para que los cambios de schema apliquen
        # al re-run; `doctype_to_temporal_dict` re-sella slug + schema_version
        # vigentes. NO se re-estampa `workflow_documents.document_type_version`
        # porque este run no pasa por `persist_classified_documents`.
        document_types = [
            doctype_to_temporal_dict(dt)
            for dt in await self.document_type_repository.list_by_workflow(self.workflow_id, self.tenant_id)
        ]

        dispatched: list[dict[str, str]] = []
        for s in sets:
            docs = documents_by_set.get(s.uuid, [])
            if not docs:
                # The set exists but has zero persisted children — nothing
                # to re-extract. Skip silently, since this is a recoverable
                # corruption rather than a user-facing error.
                logger.warning(
                    "re_extract.skip.empty_set",
                    processing_job_uuid=str(s.uuid),
                )
                continue

            await self._dispatch_for_set(s, docs, document_types, dispatched, recipe)

        if not dispatched:
            raise NoDocumentsToAnalyzeError(str(self.case_id))

        return {
            "caseId": str(self.case_id),
            "workflowId": str(self.workflow_id),
            "dispatched": dispatched,
        }

    async def _require_workflow(self) -> None:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))

    async def _require_case(self) -> None:
        case = await self.workflow_case_repository.find_by_id(self.case_id, self.tenant_id)
        if case is None or case.workflow_id != self.workflow_id:
            raise CaseNotFoundError(str(self.case_id))

    async def _require_no_active_analysis_run(self) -> None:
        active = await self.analysis_run_repository.find_active_for_case(self.case_id, self.tenant_id)
        if active is not None:
            raise AnalysisAlreadyRunningError(str(self.case_id))

    async def _require_re_extract_recipe(self):
        # ADR 0002: re-extracción corre el pipeline PROPIO del workflow; el
        # sub-segmento extract-only lo selecciona ``entry_point="reextract"``.
        recipe = await self.pipeline_repository.find_by_workflow(self.workflow_id, self.tenant_id)
        if recipe is None or recipe.current_version is None:
            raise WorkflowPipelineNotConfiguredError(str(self.workflow_id))
        return recipe

    async def _require_sets_in_case(self) -> list[WorkflowProcessingJob]:
        sets = await self.processing_job_repository.list_by_workflow(
            workflow_id=self.workflow_id,
            tenant_id=self.tenant_id,
            workflow_case_id=self.case_id,
        )
        if not sets:
            raise NoDocumentsToAnalyzeError(str(self.case_id))
        return sets

    def _require_no_in_flight(self, sets: list[WorkflowProcessingJob]) -> None:
        in_flight = [s for s in sets if not s.status.is_terminal]
        if in_flight:
            raise ExtractionInProgressError(str(self.case_id))

    async def _load_documents(self, sets: list[WorkflowProcessingJob]) -> dict[UUID, list[WorkflowDocumentRef]]:
        all_docs = await self.document_repository.list_by_processing_job_ids([s.uuid for s in sets], self.tenant_id)
        grouped: dict[UUID, list[WorkflowDocumentRef]] = {}
        for d in all_docs:
            if d.processing_job_id is None or d.document_index is None:
                continue
            grouped.setdefault(d.processing_job_id, []).append(
                WorkflowDocumentRef(
                    document_id=d.uuid,
                    document_type_id=d.document_type_id,
                    document_type_name=None,
                    document_index=d.document_index,
                    page_range=d.page_range,
                )
            )
        # Stable ordering by document_index so the lambda response can be
        # matched back deterministically.
        for refs in grouped.values():
            refs.sort(key=lambda r: r.document_index)
        return grouped

    async def _dispatch_for_set(
        self,
        processing_job: WorkflowProcessingJob,
        docs: list[WorkflowDocumentRef],
        document_types: list[dict],
        dispatched: list[dict[str, str]],
        recipe,
    ) -> None:
        if not processing_job.classified_pages:
            raise ClassifiedPagesMissingError(str(processing_job.uuid))

        # The Temporal workflow id has to be unique per dispatch so retrying
        # doesn't collide with the original processing job id (which uses
        # the same `CASE#…_FILE#…` namespace). The seq suffix keeps it
        # idempotent on duplicate calls within the same monotonic step.
        re_extract_job_id = f"REEXTRACT#{processing_job.uuid.hex}_seq{processing_job.last_seq}"

        # Run extract-only del intérprete (ADR 0002): pipeline PROPIO del workflow
        # con ``entry_point="reextract"`` (sub-segmento ``extract_fields`` →
        # ``finalize`` sin webhook), los artefactos del run original sembrados
        # — sin re-OCR — y el seq continuado para que el replay del FE no descarte
        # eventos.
        workflow_input = PipelineRunInput(
            pipeline_id=recipe.uuid,
            version=recipe.current_version,
            entry_point="reextract",
            document=DocumentProcessingInput(
                object_key="",
                document_types=document_types,
                job_id=re_extract_job_id,
                case_id=self.case_id,
                workflow_id=self.workflow_id,
                tenant_id=self.tenant_id,
                file_id=processing_job.file_id,
                file_name=None,
                processing_job_uuid=processing_job.uuid,
                persist=True,
            ),
            initial_artifacts={
                "classify_pages": {"output_uri": processing_job.classified_pages},
                "persisted_docs": [doc.model_dump(mode="json") for doc in docs],
            },
            starting_seq=processing_job.last_seq,
        )

        try:
            handle = await self.temporal_client.start_workflow(
                PipelineInterpreterWorkflow.run,
                workflow_input,
                id=re_extract_job_id,
                task_queue=self.task_queue,
            )
            dispatched.append({"setId": str(processing_job.uuid), "jobId": handle.id})
        except WorkflowAlreadyStartedError:
            logger.info(
                "re_extract.already_started",
                processing_job_uuid=str(processing_job.uuid),
                job_id=re_extract_job_id,
            )
            dispatched.append({"setId": str(processing_job.uuid), "jobId": re_extract_job_id})
