from dataclasses import dataclass
from typing import Any

from src.common.application.helpers.datetimes import optional_datetime_string
from src.common.application.helpers.json_encoder import RawJson
from src.common.domain.interfaces.presenter import Presenter
from src.common.domain.models.workflow_event import WorkflowEvent


@dataclass
class WorkflowEventPresenter(Presenter[WorkflowEvent]):
    """Delivery-log view of a ``WorkflowEvent`` (spec §10).

    ``to_dict`` is the list/summary view (no ``payload``); ``detail_dict`` adds
    the full delivered ``payload`` for the event-detail view.
    """

    instance: WorkflowEvent

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "uuid": str(self.instance.uuid),
            "event_id": self.instance.event_id,
            "event_type": self.instance.event_type.value,
            "workflow_id": str(self.instance.workflow_id),
            "processing_job_id": (
                str(self.instance.processing_job_id) if self.instance.processing_job_id else None
            ),
            "document_id": str(self.instance.document_id) if self.instance.document_id else None,
            "destination_id": (
                str(self.instance.destination_id) if self.instance.destination_id else None
            ),
            "document_status": self.instance.document_status,
            "delivery_status": self.instance.delivery_status.value,
            "attempts": self.instance.attempts,
            "response_status": self.instance.response_status,
            "last_error": self.instance.last_error,
            "last_attempt_at": optional_datetime_string(self.instance.last_attempt_at),
            "delivered_at": optional_datetime_string(self.instance.delivered_at),
            "created_at": optional_datetime_string(self.instance.created_at),
            "updated_at": optional_datetime_string(self.instance.updated_at),
        }

    @property
    def detail_dict(self) -> dict[str, Any]:
        return {**self.to_dict, "payload": RawJson(self.instance.payload)}
