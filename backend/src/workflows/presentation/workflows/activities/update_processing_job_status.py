"""Activity that mutates `workflow_processing_jobs` row state at step boundaries.

Writes `{status, current_step, last_seq, error}` plus optional artifact
keys (`extracted_text`, `classified_pages`) emitted by the first two
pipeline steps.

Idempotent on `(processing_job_uuid, last_seq)`: if the row's `last_seq`
is already greater than or equal to the incoming value the activity is
a no-op, which is what makes Temporal's at-least-once activity execution
safe.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity

from src.common.application.logging import get_logger
from src.common.database.models.workflow_processing_job import WorkflowProcessingJobORM
from src.common.domain.enums.processing_job_events import JobStatus
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    UpdateWorkflowProcessingJobStatusInput,
)

_TERMINAL_STATUSES = {JobStatus.COMPLETED, JobStatus.PARTIAL, JobStatus.FAILED}

logger = get_logger(__name__)


class UpdateWorkflowProcessingJobStatusActivity:
    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    @activity.defn(name="update_workflow_processing_job_status")
    async def update_workflow_processing_job_status(self, payload: UpdateWorkflowProcessingJobStatusInput) -> None:
        data = UpdateWorkflowProcessingJobStatusInput.model_validate(payload)

        values: dict = {
            "status": data.status.value,
            "last_seq": data.last_seq,
        }
        if data.current_step is not None:
            values["current_step"] = data.current_step.value
        if data.error is not None:
            values["error"] = json.dumps(data.error)
        if data.extracted_text_key is not None:
            values["extracted_text"] = data.extracted_text_key
        if data.classified_pages_key is not None:
            values["classified_pages"] = data.classified_pages_key

        # Wall-clock timing — captured here (not in the workflow) so the
        # numbers reflect activity execution time and survive replays. The
        # COALESCE on `started_at` keeps the first-claim baseline stable
        # across retries; `finished_at` is only stamped on the terminal hop.
        now = datetime.now(UTC)
        if data.status == JobStatus.PROCESSING:
            values["started_at"] = func.coalesce(WorkflowProcessingJobORM.started_at, now)
        elif data.status in _TERMINAL_STATUSES:
            values["finished_at"] = now
            # Cover the edge case where the very first checkpoint we see is
            # already terminal (no prior PROCESSING update was applied).
            values["started_at"] = func.coalesce(WorkflowProcessingJobORM.started_at, now)

        async with self._session_maker() as session:
            await session.execute(
                update(WorkflowProcessingJobORM)
                .where(
                    WorkflowProcessingJobORM.uuid == data.processing_job_uuid,
                    WorkflowProcessingJobORM.last_seq < data.last_seq,
                )
                .values(**values)
            )
            await session.commit()
