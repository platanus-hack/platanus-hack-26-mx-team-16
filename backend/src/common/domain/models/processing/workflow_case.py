from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.domain.enums.workflow_cases import WorkflowCaseStatus


class WorkflowCase(BaseModel):
    uuid: UUID = Field(...)
    tenant_id: UUID = Field(...)
    workflow_id: UUID = Field(...)
    name: str = Field(..., min_length=1, max_length=255)
    status: WorkflowCaseStatus = Field(default=WorkflowCaseStatus.RECEIVING)
    last_ocr_provider: str | None = Field(default=None)
    # E3 · M2M: id del sistema del cliente + receta elegida en POST /v1/cases.
    external_ref: str | None = Field(default=None, max_length=255)
    pipeline_id: UUID | None = Field(default=None)
    # E4: versión sellada al arrancar el CASE# workflow + completitud.
    pipeline_version_id: UUID | None = Field(default=None)
    # E5 · fan-out (Caso 3): lineage padre→children; NULL en casos normales.
    parent_case_id: UUID | None = Field(default=None)
    ready_at: datetime | None = Field(default=None)
    completeness: dict[str, Any] | None = Field(default=None)
    created_by: UUID | None = Field(default=None)
    created_at: datetime | None = Field(default=None)
    updated_at: datetime | None = Field(default=None)

    model_config = ConfigDict(
        from_attributes=True,
        extra="ignore",
    )

    @property
    def persist_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "workflow_id": self.workflow_id,
            "name": self.name,
            "status": self.status,
            "last_ocr_provider": self.last_ocr_provider,
            "external_ref": self.external_ref,
            "pipeline_id": self.pipeline_id,
            "pipeline_version_id": self.pipeline_version_id,
            "parent_case_id": self.parent_case_id,
            "ready_at": self.ready_at,
            "completeness": self.completeness,
            "created_by": self.created_by,
        }
