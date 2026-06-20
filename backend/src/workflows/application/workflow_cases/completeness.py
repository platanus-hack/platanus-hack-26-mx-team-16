"""Evaluación de completitud del expediente (E4 · await_documents + API).

Compartida por la activity ``evaluate_case_completeness`` (persiste snapshot +
case_event ``completeness.evaluated`` SOLO si cambió) y por los endpoints
``GET …/completeness`` (cálculo fresco, ``persist=False``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.application.workflow_cases.recipe_resolver import resolve_case_recipe
from src.workflows.domain.models.case_event import CaseEvent
from src.workflows.domain.models.phase_configs import completeness_dict_from_version
from src.workflows.domain.models.policies import CompletenessPolicy
from src.workflows.domain.repositories.case_event import CaseEventRepository
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.domain.services.case_completeness import compute_case_completeness

COMPLETENESS_EVALUATED_EVENT = "completeness.evaluated"


@dataclass
class CaseCompletenessResult:
    case: WorkflowCase
    policy: CompletenessPolicy | None
    snapshot: dict[str, Any]  # {satisfied, required, present, missing}
    changed: bool

    @property
    def satisfied(self) -> bool:
        return bool(self.snapshot.get("satisfied"))

    @property
    def auto_ready(self) -> bool:
        return bool(self.policy.auto_ready) if self.policy else False


@dataclass
class EvaluateCaseCompleteness(UseCase):
    tenant_id: UUID
    case_id: UUID
    case_repository: WorkflowCaseRepository
    document_repository: WorkflowDocumentRepository
    document_type_repository: DocumentTypeRepository
    pipeline_repository: PipelineRepository
    workflow_repository: WorkflowRepository | None = None
    case_event_repository: CaseEventRepository | None = None
    persist: bool = False
    # Binding opcional al workflow del path (endpoints JWT): caso de otro
    # workflow del tenant ⇒ 404.
    workflow_id: UUID | None = None

    async def execute(self) -> CaseCompletenessResult:
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if case is None:
            raise CaseNotFoundError(str(self.case_id))
        if self.workflow_id is not None and case.workflow_id != self.workflow_id:
            raise CaseNotFoundError(str(self.case_id))

        policy = await self._resolve_policy(case)
        documents = await self.document_repository.list_by_case(self.case_id, self.tenant_id)
        doc_types = await self.document_type_repository.list_by_workflow(case.workflow_id, self.tenant_id)
        slug_by_type_id = {dt.uuid: dt.slug for dt in doc_types if dt.slug}

        snapshot = compute_case_completeness(documents, slug_by_type_id, policy)
        changed = snapshot != case.completeness

        if self.persist and changed:
            case.completeness = snapshot
            case = await self.case_repository.update(case)
            if self.case_event_repository is not None:
                await self.case_event_repository.create(
                    CaseEvent(
                        uuid=uuid4(),
                        tenant_id=self.tenant_id,
                        case_id=self.case_id,
                        type=COMPLETENESS_EVALUATED_EVENT,
                        payload=snapshot,
                        actor="system",
                    )
                )
        return CaseCompletenessResult(case=case, policy=policy, snapshot=snapshot, changed=changed)

    async def _resolve_policy(self, case: WorkflowCase) -> CompletenessPolicy | None:
        version = await resolve_case_recipe(
            case,
            self.tenant_id,
            pipeline_repository=self.pipeline_repository,
            workflow_repository=self.workflow_repository,
        )
        if version is None:
            return None
        # D-A: completitud plegada en await_documents.config (única fuente, sin fallback version-level).
        raw = completeness_dict_from_version(version)
        if raw is None:
            return None
        return CompletenessPolicy.model_validate(raw)
