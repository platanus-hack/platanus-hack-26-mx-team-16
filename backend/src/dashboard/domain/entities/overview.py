"""Domain entities for the Dashboard Overview tab.

The Overview tab shows tenant-wide aggregates: total documents, monthly
throughput chart and a list of recently updated documents.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.common.domain.enums.workflows import WorkflowDocumentStatus


class StatDelta(BaseModel):
    """Counter with a percentage delta vs. the previous calendar month.

    `delta_pct` is None when the previous-period count was 0 (avoids
    dividing by zero and signals "no baseline" to the frontend).
    """

    model_config = ConfigDict(from_attributes=True)

    value: int
    delta_pct: float | None = None


class QueueDelta(BaseModel):
    """Live counter with a delta vs. a snapshot taken one hour ago.

    `delta_since_last_hour` is None when no hourly snapshot is available
    (e.g. before the snapshot job has run for the first time).
    """

    model_config = ConfigDict(from_attributes=True)

    value: int
    delta_since_last_hour: int | None = None


class OverviewSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_documents: StatDelta
    documents_processed: StatDelta
    active_workflows: StatDelta
    processing_queue: QueueDelta


class ThroughputBucket(BaseModel):
    """One bucket of the monthly throughput bar chart."""

    model_config = ConfigDict(from_attributes=True)

    label: str
    year: int
    month: int
    total: int


class RecentDocument(BaseModel):
    """A workflow document shown in the "Recent Documents" card.

    `page_count` is derived from `workflow_documents.extraction_pages`
    when available; None when the document has not been processed yet
    or pages were not persisted.
    """

    model_config = ConfigDict(from_attributes=True)

    uuid: UUID
    name: str
    workflow_slug: str
    workflow_name: str
    status: WorkflowDocumentStatus
    page_count: int | None
    created_at: datetime
    updated_at: datetime


class OverviewData(BaseModel):
    """Composite payload returned by `GET /v1/dashboard/overview`."""

    model_config = ConfigDict(from_attributes=True)

    summary: OverviewSummary
    throughput: list[ThroughputBucket]
    recent_documents: list[RecentDocument]
