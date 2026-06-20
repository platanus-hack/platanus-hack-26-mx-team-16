from dataclasses import dataclass, field
from typing import Any

from src.common.application.helpers.uuids import optional_string
from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.workflow_processing_job import WorkflowProcessingJob


@dataclass
class WorkflowProcessingJobPresenter(Presenter[WorkflowProcessingJob]):
    instance: WorkflowProcessingJob
    file_name: str | None = None
    documents: list[WorkflowDocument] = field(default_factory=list)

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "set_id": str(self.instance.uuid),
            "temporal_workflow_id": self.instance.temporal_workflow_id,
            "tenant_id": str(self.instance.tenant_id),
            "workflow_id": str(self.instance.workflow_id),
            "workflow_case_id": optional_string(self.instance.workflow_case_id),
            "file_id": str(self.instance.file_id),
            "file_name": self.file_name,
            "status": self.instance.status.value,
            "current_step": self.instance.current_step,
            "last_seq": self.instance.last_seq,
            "attempts": self.instance.attempts,
            "error": self.instance.error,
            "result_summary": self.instance.result_summary,
            "trigger": self.instance.trigger.value,
            "created_by_id": optional_string(self.instance.created_by_id),
            "started_at": optional_datetime_string(self.instance.started_at),
            "finished_at": optional_datetime_string(self.instance.finished_at),
            "duration_ms": self.instance.duration_ms,
            "document_count": len(self.documents),
            "documents": [
                {
                    "uuid": str(document.uuid),
                    "name": document.file_name,
                    "document_type_id": optional_string(document.document_type_id),
                    "document_index": document.document_index,
                    "page_range": document.page_range,
                    "status": str(document.status),
                    "processing_status": document.processing_status,
                }
                for document in self.documents
            ],
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }
