"""I/O de la activity de transición de estado del caso (E4 · diseño §1)."""

from uuid import UUID

from pydantic import BaseModel


class TransitionCaseStatusInput(BaseModel):
    tenant_id: UUID
    case_id: UUID
    to_status: str  # WorkflowCaseStatus.value
    reason: str | None = None
    actor: str | None = None


class TransitionCaseStatusOutput(BaseModel):
    case_id: UUID
    status: str  # estado final persistido (WorkflowCaseStatus.value)
    changed: bool  # False ⇒ no-op idempotente (mismo estado)
