from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProcessRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    tenant_id: UUID
    workflow_id: UUID | None
    workflow_name: str | None = None
    object_key_digest: str
    page_count: int
    analysis_run_id: UUID | None
    processed_at: datetime
    created_at: datetime
