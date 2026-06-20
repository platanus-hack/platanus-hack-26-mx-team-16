"""Activity that records one recipe-phase boundary into ``workflow_phase_executions``.

Called by the interpreter (``PipelineInterpreterWorkflow``) at the start and end
of every phase via the ``on_phase`` hook of ``execute_pipeline``. It is the only
writer of the per-phase execution timeline that powers the "Ejecuciones" view.

Idempotent on ``(processing_job_id, seq)`` so Temporal's at-least-once activity
delivery never double-inserts a phase row.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker
from temporalio import activity

from src.common.application.logging import get_logger
from src.common.domain.enums.pipelines import PhaseExecutionEvent, PhaseExecutionStatus
from src.workflows.infrastructure.repositories.sql_workflow_phase_execution import (
    SQLWorkflowPhaseExecutionRepository,
)
from src.workflows.presentation.workflows.activities.processing_job_event_inputs import (
    RecordPhaseExecutionInput,
)

logger = get_logger(__name__)


class RecordPhaseExecutionActivity:
    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._session_maker = session_maker

    @activity.defn(name="record_phase_execution")
    async def record_phase_execution(self, payload: RecordPhaseExecutionInput) -> None:
        data = RecordPhaseExecutionInput.model_validate(payload)

        async with self._session_maker() as session:
            repo = SQLWorkflowPhaseExecutionRepository(session)
            if data.event == PhaseExecutionEvent.STARTED:
                await repo.record_started(
                    processing_job_id=data.processing_job_uuid,
                    tenant_id=data.tenant_id,
                    seq=data.seq,
                    phase_id=data.phase_id,
                    phase_kind=data.phase_kind,
                    started_at=data.started_at,
                )
            else:
                status = (
                    PhaseExecutionStatus.FAILED
                    if data.event == PhaseExecutionEvent.FAILED
                    else PhaseExecutionStatus.COMPLETED
                )
                await repo.record_finished(
                    processing_job_id=data.processing_job_uuid,
                    tenant_id=data.tenant_id,
                    seq=data.seq,
                    phase_id=data.phase_id,
                    phase_kind=data.phase_kind,
                    status=status,
                    started_at=data.started_at,
                    finished_at=data.finished_at,
                    output_snapshot=data.output_snapshot,
                    error=data.error,
                )
            await session.commit()
