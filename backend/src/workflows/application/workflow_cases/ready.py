"""POST …/ready — marcar el expediente listo (E4 · diseño §7).

Idempotente: ya ready ⇒ no-op; receta sin ``await_documents`` ⇒ no-op
(data-only arranca solo, E3). Faltantes sin ``force`` ⇒ 409
``case.not_complete`` con ``missing`` en el detalle (el FE lo lee de
``errors[0].missing``). OK ⇒ asegura el CASE# y señala ``case_ready {force}``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from temporalio.client import Client as TemporalClient

from src.common.domain.exceptions._base import DomainError
from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.application.workflow_cases.case_run_starter import (
    CASE_READY_SIGNAL,
    EnsureCaseRunStarted,
    signal_case_run,
)
from src.workflows.application.workflow_cases.completeness import EvaluateCaseCompleteness
from src.workflows.application.workflow_cases.recipe_resolver import (
    recipe_has_await_documents,
    resolve_case_recipe,
)
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository


class CaseNotCompleteError(DomainError):
    def __init__(self, case_id: str, missing: list[dict[str, Any]]):
        super().__init__(
            code="case.not_complete",
            message="The case is missing required documents. Retry with force=true to override.",
            status_code=409,
            context={"case_id": case_id, "missing": missing},
        )


class CaseReadySignalError(DomainError):
    def __init__(self, case_id: str):
        super().__init__(
            code="case.signal_failed",
            message="Could not deliver the ready signal to the case run. Retry shortly.",
            status_code=503,
            context={"case_id": case_id},
        )


@dataclass
class RequestCaseReadyResult:
    case: WorkflowCase
    # "signaled" | "already_ready" | "no_await_documents"
    outcome: str
    completeness: dict[str, Any] | None = None


@dataclass
class RequestCaseReady(UseCase):
    tenant_id: UUID
    case_id: UUID
    case_repository: WorkflowCaseRepository
    document_repository: WorkflowDocumentRepository
    document_type_repository: DocumentTypeRepository
    pipeline_repository: PipelineRepository
    temporal_client: TemporalClient
    task_queue: str
    workflow_repository: WorkflowRepository | None = None
    force: bool = False
    # Binding opcional al workflow del path (endpoints JWT): un caso de OTRO
    # workflow del mismo tenant es 404, no mutable (espejo de ResolveIngestCase).
    workflow_id: UUID | None = None

    async def execute(self) -> RequestCaseReadyResult:
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if case is None:
            raise CaseNotFoundError(str(self.case_id))
        if self.workflow_id is not None and case.workflow_id != self.workflow_id:
            raise CaseNotFoundError(str(self.case_id))

        version = await resolve_case_recipe(
            case,
            self.tenant_id,
            pipeline_repository=self.pipeline_repository,
            workflow_repository=self.workflow_repository,
        )
        if not recipe_has_await_documents(version):
            return RequestCaseReadyResult(case=case, outcome="no_await_documents")

        if case.ready_at is not None:
            return RequestCaseReadyResult(
                case=case, outcome="already_ready", completeness=case.completeness
            )

        completeness = await EvaluateCaseCompleteness(
            tenant_id=self.tenant_id,
            case_id=self.case_id,
            case_repository=self.case_repository,
            document_repository=self.document_repository,
            document_type_repository=self.document_type_repository,
            pipeline_repository=self.pipeline_repository,
            workflow_repository=self.workflow_repository,
            persist=False,
        ).execute()

        if not completeness.satisfied and not self.force:
            raise CaseNotCompleteError(str(self.case_id), completeness.snapshot.get("missing") or [])

        await EnsureCaseRunStarted(
            tenant_id=self.tenant_id,
            case_id=self.case_id,
            case_repository=self.case_repository,
            pipeline_repository=self.pipeline_repository,
            workflow_repository=self.workflow_repository,
            temporal_client=self.temporal_client,
            task_queue=self.task_queue,
        ).execute()
        signaled = await signal_case_run(
            self.temporal_client, self.case_id, CASE_READY_SIGNAL, {"force": self.force}
        )
        if not signaled:
            # La señal ES la operación: sin ella el CASE# queda esperando hasta
            # el próximo documento. 503 ⇒ el cliente reintenta (idempotente:
            # ready_at lo sella el workflow al proceder, no este use case).
            raise CaseReadySignalError(str(self.case_id))
        return RequestCaseReadyResult(
            case=case, outcome="signaled", completeness=completeness.snapshot
        )
