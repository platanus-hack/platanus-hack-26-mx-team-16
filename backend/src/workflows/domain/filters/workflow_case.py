from datetime import datetime
from uuid import UUID
from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from src.common.application.helpers.datetimes import parse_filter_date_from, parse_filter_date_to
from src.common.domain.entities.common.collection import ListFilters
from src.common.domain.enums.workflow_cases import WorkflowCaseStatus


class WorkflowCaseFilters(ListFilters):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    """Cursor-based filters for the cases list endpoint.

    Inherits: cursor (str|None), limit (int=25)
    """
    search: str | None = None
    statuses: str | None = None  # CSV: "RECEIVING,PROCESSING" (E4: 11 estados)
    document_types: str | None = None  # CSV de UUIDs: "uuid1,uuid2"
    date_from: str | None = None
    date_to: str | None = None
    # E5 · fan-out: listar los children de un padre (query param parentCaseId).
    parent_case_id: str | None = None
    # Re-IA 2026-06: solo casos con algún run de procesamiento FAILED
    # (query param withFailedRuns) — el badge/filtro «Con errores» del FE.
    with_failed_runs: bool | None = None

    @property
    def parsed_date_from(self) -> datetime | None:
        return parse_filter_date_from(self.date_from)

    @property
    def parsed_date_to(self) -> datetime | None:
        return parse_filter_date_to(self.date_to)

    @property
    def enum_statuses(self) -> list[WorkflowCaseStatus]:
        return self.parse_enum_values(self.statuses, WorkflowCaseStatus)

    @property
    def doctype_uuids(self) -> list[UUID]:
        if not self.document_types:
            return []
        return [UUID(v.strip()) for v in self.document_types.split(",") if v.strip()]

    @property
    def parent_case_uuid(self) -> UUID | None:
        if not self.parent_case_id:
            return None
        return UUID(self.parent_case_id.strip())
