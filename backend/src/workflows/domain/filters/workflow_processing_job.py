from datetime import datetime
from uuid import UUID
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel
from src.common.application.helpers.datetimes import parse_filter_date_from, parse_filter_date_to
from src.common.domain.entities.common.collection import ListFilters
from src.common.domain.enums.workflows import WorkflowProcessingJobStatus


class WorkflowProcessingJobFilters(ListFilters):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    search: str | None = None
    statuses: str | None = None  # CSV: "COMPLETED,FAILED"
    document_types: str | None = None  # CSV de UUIDs: "uuid1,uuid2"
    workflow_case_id: UUID | None = None
    date_from: str | None = None
    date_to: str | None = None

    @property
    def parsed_date_from(self) -> datetime | None:
        return parse_filter_date_from(self.date_from)

    @property
    def parsed_date_to(self) -> datetime | None:
        return parse_filter_date_to(self.date_to)

    @property
    def enum_statuses(self) -> list[WorkflowProcessingJobStatus]:
        return self.parse_enum_values(self.statuses, WorkflowProcessingJobStatus)

    @property
    def doctype_uuids(self) -> list[UUID]:
        if not self.document_types:
            return []
        return [UUID(v.strip()) for v in self.document_types.split(",") if v.strip()]
