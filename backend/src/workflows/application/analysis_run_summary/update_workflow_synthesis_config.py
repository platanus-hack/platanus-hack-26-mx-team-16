"""Update the per-workflow synthesis configuration (synthesis spec §9, §11 Fase 3)."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import jsonschema

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow import Workflow
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.run_summary.errors import OutputSchemaInvalidError
from src.workflows.domain.services.prompt_renderer import (
    TokenPromptRenderer,
    UnknownTokenError,
)


@dataclass
class UpdateWorkflowSynthesisConfig(UseCase):
    workflow_id: UUID
    tenant_id: UUID
    output_schema: dict[str, Any] | None
    synthesis_template: str | None
    synthesis_enabled: bool
    workflow_repository: WorkflowRepository

    async def execute(self) -> Workflow:
        workflow = await self.workflow_repository.find_by_id(self.workflow_id, self.tenant_id)
        if workflow is None:
            raise WorkflowNotFoundError(str(self.workflow_id))

        if self.output_schema is not None:
            try:
                jsonschema.Draft7Validator.check_schema(self.output_schema)
            except jsonschema.SchemaError as exc:
                raise OutputSchemaInvalidError(exc.message) from exc

        if self.synthesis_template:
            renderer = TokenPromptRenderer()
            try:
                renderer.assert_valid(self.synthesis_template)
            except UnknownTokenError:
                raise

        workflow.output_schema = self.output_schema
        workflow.synthesis_template = self.synthesis_template
        workflow.synthesis_enabled = self.synthesis_enabled
        return await self.workflow_repository.update(workflow)
