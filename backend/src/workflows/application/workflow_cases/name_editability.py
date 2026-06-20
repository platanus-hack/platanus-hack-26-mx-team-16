"""Guard de editabilidad del nombre del caso (cases-table-upload · B1, D3).

El nombre del caso solo es editable cuando la receta del caso tiene una fase
``await_documents`` (capability ``multi_doc_dossier``): el expediente que el
usuario crea y nombra. En cualquier otra forma (``per_upload``) el nombre lo
fija el archivo (``_ensure_case`` del dispatcher) y no es editable por el
usuario. Los clientes M2M quedan exentos (gestionan su propio naming) — este
guard solo protege los caminos JWT (alta + rename).
"""

from __future__ import annotations

from uuid import UUID

from src.common.domain.exceptions._base import DomainError
from src.common.domain.models.processing.workflow_case import WorkflowCase
from src.workflows.application.workflow_cases.recipe_resolver import (
    recipe_has_await_documents,
    resolve_case_recipe,
)
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository


class CaseNameNotEditableError(DomainError):
    def __init__(self, case_id: str):
        super().__init__(
            code="case.name_not_editable",
            message=(
                "The case name is derived from its document and cannot be set; "
                "naming is only editable on multi-document dossier workflows."
            ),
            status_code=422,
            context={"case_id": case_id},
        )


async def case_name_is_editable(
    case: WorkflowCase,
    tenant_id: UUID,
    pipeline_repository: PipelineRepository,
    workflow_repository: WorkflowRepository | None = None,
) -> bool:
    version = await resolve_case_recipe(
        case,
        tenant_id,
        pipeline_repository=pipeline_repository,
        workflow_repository=workflow_repository,
    )
    return recipe_has_await_documents(version)
