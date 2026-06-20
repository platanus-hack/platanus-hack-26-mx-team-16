"""Comentario del caso como case_event ``comment.added`` (E5 · diseño §8.1).

El timeline ya pinta eventos: un comentario es un evento append-only con
``actor`` y SIN dedupe (cada comentario es único, incluso texto repetido).
Binding workflow→caso (patrón E4 anti-IDOR): caso de otro workflow ⇒ 404.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.common.domain.exceptions.processing import CaseNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.workflows.domain.models.case_event import CaseEvent
from src.workflows.domain.repositories.case_event import CaseEventRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository

COMMENT_ADDED_EVENT = "comment.added"


@dataclass
class AddCaseComment(UseCase):
    tenant_id: UUID
    case_id: UUID
    body: str
    case_repository: WorkflowCaseRepository
    case_event_repository: CaseEventRepository
    actor: str | None = None
    workflow_id: UUID | None = None

    async def execute(self) -> CaseEvent:
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if case is None:
            raise CaseNotFoundError(str(self.case_id))
        if self.workflow_id is not None and case.workflow_id != self.workflow_id:
            raise CaseNotFoundError(str(self.case_id))

        return await self.case_event_repository.create(
            CaseEvent(
                uuid=uuid4(),
                tenant_id=self.tenant_id,
                case_id=self.case_id,
                type=COMMENT_ADDED_EVENT,
                payload={"body": self.body},
                actor=self.actor,
                dedupe_key=None,  # cada comentario es único — sin dedupe
            )
        )
