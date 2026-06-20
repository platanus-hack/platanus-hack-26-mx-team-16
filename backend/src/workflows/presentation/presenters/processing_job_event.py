from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.uuids import optional_string
from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.domain.interfaces.presenter import Presenter
from src.workflows.domain.events import ProcessingJobEvent


@dataclass
class ProcessingJobEventPresenter(Presenter[ProcessingJobEvent]):
    instance: ProcessingJobEvent

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.instance.type.value,
            "seq": self.instance.seq,
            "ts": optional_datetime_string(self.instance.ts),
            "workflow_id": optional_string(self.instance.workflow_id),
            "processing_job_id": optional_string(self.instance.processing_job_id),
            "workflow_case_id": optional_string(self.instance.workflow_case_id),
            "document_id": optional_string(self.instance.document_id),
            "payload": self.instance.payload,
        }
