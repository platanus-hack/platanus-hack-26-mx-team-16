from typing import Any

from pydantic import Field

from src.common.domain.entities.common.requests import CamelCaseRequest


class UpdateWorkflowOutputSchemaRequest(CamelCaseRequest):
    output_schema: dict[str, Any] | None = Field(default=None)
    synthesis_template: str | None = Field(default=None)
    synthesis_enabled: bool = Field(default=False)
