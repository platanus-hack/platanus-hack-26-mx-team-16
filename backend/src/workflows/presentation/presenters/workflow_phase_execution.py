from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.workflow_phase_execution import WorkflowPhaseExecution


@dataclass
class WorkflowPhaseExecutionPresenter(Presenter[WorkflowPhaseExecution]):
    instance: WorkflowPhaseExecution

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "processing_job_id": str(self.instance.processing_job_id),
            "seq": self.instance.seq,
            "phase_id": self.instance.phase_id,
            "phase_kind": self.instance.phase_kind,
            "status": self.instance.status.value,
            "started_at": optional_datetime_string(self.instance.started_at),
            "finished_at": optional_datetime_string(self.instance.finished_at),
            "duration_ms": self.instance.duration_ms,
            "output_snapshot": self.instance.output_snapshot,
            "error": self.instance.error,
            "created_at": optional_datetime_string(self.instance.created_at),
        }
