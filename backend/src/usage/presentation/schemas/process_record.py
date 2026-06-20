from uuid import UUID

from pydantic import BaseModel, Field


class CreateProcessRecordSchema(BaseModel):
    workflow_id: UUID | None = Field(default=None)
    object_key_digest: str = Field(..., max_length=64)
    page_count: int = Field(..., ge=1)
    analysis_run_id: UUID | None = Field(default=None)
