"""Temporal activity that records page-level usage after document classification.

Runs once per workflow execution, right after `persist_classified_documents`,
when the total page count is known. Calls the repository directly (bypassing
the quota check in CreateProcessRecord use case) so usage is always recorded
even when the tenant has exceeded their quota.
"""

from __future__ import annotations

import hashlib

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity

from src.usage.domain.models.process_record import ProcessRecord
from src.usage.infrastructure.repositories.sql_process_record import SQLProcessRecordRepository


class CreateProcessRecordInput(BaseModel):
    tenant_id: UUID
    workflow_id: UUID | None
    object_key: str
    page_count: int
    analysis_run_id: UUID | None = None


@dataclass
class CreateProcessRecordActivity:
    session_maker: async_sessionmaker

    @activity.defn(name="create_process_record")
    async def create_process_record(self, raw_input: dict) -> dict:
        data = CreateProcessRecordInput.model_validate(raw_input)
        object_key_hash = hashlib.sha256(data.object_key.encode("utf-8")).hexdigest()

        now = datetime.now(UTC)
        record = ProcessRecord(
            uuid=uuid4(),
            tenant_id=data.tenant_id,
            workflow_id=data.workflow_id,
            object_key_digest=object_key_hash,
            page_count=data.page_count,
            analysis_run_id=data.analysis_run_id,
            processed_at=now,
            created_at=now,
        )

        async with self.session_maker() as session:
            repo = SQLProcessRecordRepository(session=session)
            record = await repo.create(record)

        return {"process_record_id": str(record.uuid)}
