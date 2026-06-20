"""SQL implementation of `DashboardMetricsRepository`.

All queries are tenant-scoped (the `tenant_id` filter is always the first
predicate). Timezone math for "current calendar month" and "today" is
performed in Python with `ZoneInfo` and the resulting UTC boundaries are
passed to PostgreSQL — keeps SQL DB-portable and avoids per-row
`AT TIME ZONE` overhead.

The v1 fallback documented in the spec is implemented here: when
`workflow_documents.processing_status` is NULL, all `PROCESSING` rows
collapse into the single `PROCESSING` stage bucket and the same fallback
applies to `list_live_processing`.

PERFORMANCE — required index:
    CREATE INDEX ON workflow_documents (tenant_id, status, created_at);
The existing `ix_wf_docs_workflow_status` is `(workflow_id, status)` and
does NOT cover the tenant-scoped patterns used here. See
`product/plans/dashboard/dashboard-data.md` § "Performance & escalabilidad" for context.
This index has to be added in a migration before the endpoints are
exposed in production.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database.models.workflow_document import WorkflowDocumentORM
from src.common.database.models.workspace import WorkflowORM
from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.dashboard.domain.entities.overview import (
    OverviewSummary,
    QueueDelta,
    RecentDocument,
    StatDelta,
    ThroughputBucket,
)
from src.dashboard.domain.entities.processing import (
    LiveProcessingDocument,
    PipelineStage,
    PipelineStageKey,
    ProcessingSummary,
)
from src.dashboard.domain.repositories.dashboard_metrics import (
    DashboardMetricsRepository,
)

_ONE_DAY = timedelta(days=1)
_MONTHS_IN_YEAR = 12

_MONTH_LABELS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)

_STAGE_LABELS: dict[PipelineStageKey, str] = {
    PipelineStageKey.UPLOAD: "Upload",
    PipelineStageKey.OCR: "OCR",
    PipelineStageKey.EXTRACTION: "Extraction",
    PipelineStageKey.VALIDATION: "Validation",
    PipelineStageKey.PROCESSING: "Processing",
    PipelineStageKey.COMPLETE: "Complete",
}

_PROGRESS_PCT_BY_STAGE: dict[PipelineStageKey, int] = {
    PipelineStageKey.UPLOAD: 10,
    PipelineStageKey.OCR: 40,
    PipelineStageKey.EXTRACTION: 70,
    PipelineStageKey.VALIDATION: 90,
    PipelineStageKey.PROCESSING: 50,  # v1 fallback when processing_status is NULL
}

# Values written to `workflow_documents.processing_status` by the Temporal
# activities (see `mark_document_status.py` and `persist_classified_documents.py`).
# These are the string values of `DocumentStatus` — kept lowercase for
# backward compatibility with rows persisted before this dashboard module
# existed. The dashboard stage names exposed to the frontend (UPLOAD,
# EXTRACTION, VALIDATION, COMPLETE) are independent.
#
# Note: the v1 pipeline has no dedicated OCR sub-stage; `_PROCESSING_STATUS_OCR`
# is reserved for forward compatibility and is currently dead code. If a
# future workflow writes "ocr" into `processing_status`, the dashboard will
# automatically render it under the OCR bucket.
_PROCESSING_STATUS_OCR = "ocr"
_PROCESSING_STATUS_EXTRACTION = "extracting"
_PROCESSING_STATUS_VALIDATION = "validating"


class SQLDashboardMetricsRepository(DashboardMetricsRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------------------- Overview ----------------------

    async def get_overview_summary(
        self,
        *,
        tenant_id: UUID,
        now: datetime,
        time_zone: str,
    ) -> OverviewSummary:
        start_curr_utc, start_prev_utc = _month_boundaries_utc(now, time_zone)

        # Single query: conditional aggregations for the three count-based stats.
        is_current_month_created = WorkflowDocumentORM.created_at >= start_curr_utc
        is_previous_month_created = (WorkflowDocumentORM.created_at >= start_prev_utc) & (
            WorkflowDocumentORM.created_at < start_curr_utc
        )
        is_current_month_processed = (WorkflowDocumentORM.status == WorkflowDocumentStatus.EXTRACTED.value) & (
            WorkflowDocumentORM.updated_at >= start_curr_utc
        )
        is_previous_month_processed = (
            (WorkflowDocumentORM.status == WorkflowDocumentStatus.EXTRACTED.value)
            & (WorkflowDocumentORM.updated_at >= start_prev_utc)
            & (WorkflowDocumentORM.updated_at < start_curr_utc)
        )
        is_in_queue_now = WorkflowDocumentORM.status.in_(
            (
                WorkflowDocumentStatus.UPLOADED.value,
                WorkflowDocumentStatus.PROCESSING.value,
            )
        )

        stmt = select(
            func.count().label("total"),
            func.sum(case((is_current_month_created, 1), else_=0)).label("created_curr"),
            func.sum(case((is_previous_month_created, 1), else_=0)).label("created_prev"),
            func.sum(case((is_current_month_processed, 1), else_=0)).label("processed_curr"),
            func.sum(case((is_previous_month_processed, 1), else_=0)).label("processed_prev"),
            func.sum(case((is_in_queue_now, 1), else_=0)).label("queue_now"),
        ).where(WorkflowDocumentORM.tenant_id == tenant_id)
        row = (await self.session.execute(stmt)).one()

        # Active workflows: distinct workflow_id with ≥1 doc created in the period.
        active_curr = await self._count_active_workflows(tenant_id=tenant_id, since=start_curr_utc)
        active_prev = await self._count_active_workflows(
            tenant_id=tenant_id, since=start_prev_utc, until=start_curr_utc
        )

        total_curr = int(row.created_curr or 0)
        total_prev = int(row.created_prev or 0)
        processed_curr = int(row.processed_curr or 0)
        processed_prev = int(row.processed_prev or 0)

        return OverviewSummary(
            total_documents=StatDelta(
                value=int(row.total or 0),
                delta_pct=_delta_pct(total_curr, total_prev),
            ),
            documents_processed=StatDelta(
                value=processed_curr,
                delta_pct=_delta_pct(processed_curr, processed_prev),
            ),
            active_workflows=StatDelta(
                value=active_curr,
                delta_pct=_delta_pct(active_curr, active_prev),
            ),
            processing_queue=QueueDelta(
                value=int(row.queue_now or 0),
                # Hourly snapshot table not implemented in v1; spec § "Snapshots
                # opcionales" calls for `null` until the snapshot job exists.
                delta_since_last_hour=None,
            ),
        )

    async def _count_active_workflows(
        self,
        *,
        tenant_id: UUID,
        since: datetime,
        until: datetime | None = None,
    ) -> int:
        # "Active" = ≥1 doc in {UPLOADED, PROCESSING, EXTRACTED} created in
        # the window — matches the spec's definition.
        #
        # Caveat: status is read at query time, not as-of the end of the
        # window. A workflow whose only docs created last month later moved
        # to ERROR will be excluded from the previous-month baseline,
        # slightly inflating the month-over-month delta. We accept this
        # minor distortion to keep `value` faithful to the spec — anything
        # else would either double-count or require a status-change audit
        # log we don't have today.
        active_statuses = (
            WorkflowDocumentStatus.UPLOADED.value,
            WorkflowDocumentStatus.PROCESSING.value,
            WorkflowDocumentStatus.EXTRACTED.value,
        )
        stmt = select(func.count(func.distinct(WorkflowDocumentORM.workflow_id))).where(
            WorkflowDocumentORM.tenant_id == tenant_id,
            WorkflowDocumentORM.status.in_(active_statuses),
            WorkflowDocumentORM.created_at >= since,
        )
        if until is not None:
            stmt = stmt.where(WorkflowDocumentORM.created_at < until)
        return int((await self.session.execute(stmt)).scalar_one() or 0)

    async def get_throughput(
        self,
        *,
        tenant_id: UUID,
        months: int,
        now: datetime,
    ) -> list[ThroughputBucket]:
        # Lower bound: start of (months - 1) months ago, in UTC. Includes the
        # current month so the chart always shows `months` data points.
        # Note: we use the server clock's calendar (UTC) for bucket boundaries
        # to keep the SQL trivial; per-tenant timezone for monthly aggregates
        # would require AT TIME ZONE in the GROUP BY and is overkill for a
        # 12-month bar chart.
        since = _months_ago_start(now, months)
        bucket = func.date_trunc("month", WorkflowDocumentORM.created_at).label("bucket")
        stmt = (
            select(bucket, func.count().label("total"))
            .where(
                WorkflowDocumentORM.tenant_id == tenant_id,
                WorkflowDocumentORM.created_at >= since,
                WorkflowDocumentORM.status == WorkflowDocumentStatus.EXTRACTED.value,
            )
            .group_by(bucket)
            .order_by(bucket)
        )
        rows = (await self.session.execute(stmt)).all()
        by_year_month: dict[tuple[int, int], int] = {(r.bucket.year, r.bucket.month): int(r.total) for r in rows}
        return _fill_missing_months(by_year_month, now=now, months=months)

    async def get_recent_documents(
        self,
        *,
        tenant_id: UUID,
        limit: int,
    ) -> list[RecentDocument]:
        stmt = (
            select(
                WorkflowDocumentORM.uuid,
                WorkflowDocumentORM.name,
                WorkflowDocumentORM.status,
                WorkflowDocumentORM.extraction_pages,
                WorkflowDocumentORM.created_at,
                WorkflowDocumentORM.updated_at,
                WorkflowORM.slug.label("workflow_slug"),
                WorkflowORM.name.label("workflow_name"),
            )
            .join(WorkflowORM, WorkflowORM.uuid == WorkflowDocumentORM.workflow_id)
            .where(WorkflowDocumentORM.tenant_id == tenant_id)
            .order_by(WorkflowDocumentORM.updated_at.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            RecentDocument(
                uuid=r.uuid,
                name=r.name,
                workflow_slug=r.workflow_slug or "",
                workflow_name=r.workflow_name,
                status=WorkflowDocumentStatus(r.status),
                page_count=len(r.extraction_pages) if r.extraction_pages else None,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ]

    # ---------------------- Processing ----------------------

    async def get_processing_summary(
        self,
        *,
        tenant_id: UUID,
        now: datetime,
        time_zone: str,
    ) -> ProcessingSummary:
        today_start_utc = _today_start_utc(now, time_zone)

        is_in_queue = WorkflowDocumentORM.status == WorkflowDocumentStatus.UPLOADED.value
        is_processing = WorkflowDocumentORM.status == WorkflowDocumentStatus.PROCESSING.value
        is_completed_today = (WorkflowDocumentORM.status == WorkflowDocumentStatus.EXTRACTED.value) & (
            WorkflowDocumentORM.updated_at >= today_start_utc
        )
        is_failed = WorkflowDocumentORM.status == WorkflowDocumentStatus.ERROR.value
        # Processing seconds = updated_at - created_at for docs completed today.
        # SQLAlchemy's func.extract is dialect-agnostic and returns float (seconds).
        seconds_completed_today = case(
            (
                is_completed_today,
                func.extract(
                    "epoch",
                    WorkflowDocumentORM.updated_at - WorkflowDocumentORM.created_at,
                ),
            ),
            else_=None,
        )

        stmt = select(
            func.sum(case((is_in_queue, 1), else_=0)).label("in_queue"),
            func.sum(case((is_processing, 1), else_=0)).label("processing"),
            func.sum(case((is_completed_today, 1), else_=0)).label("completed_today"),
            func.sum(case((is_failed, 1), else_=0)).label("failed"),
            func.avg(seconds_completed_today).label("avg_seconds"),
        ).where(WorkflowDocumentORM.tenant_id == tenant_id)
        row = (await self.session.execute(stmt)).one()

        avg = row.avg_seconds
        return ProcessingSummary(
            in_queue=int(row.in_queue or 0),
            processing=int(row.processing or 0),
            completed_today=int(row.completed_today or 0),
            failed=int(row.failed or 0),
            avg_processing_seconds=float(avg) if avg is not None else None,
        )

    async def list_pipeline_stages(
        self,
        *,
        tenant_id: UUID,
    ) -> list[PipelineStage]:
        # Bucketize each doc into a dashboard stage. PROCESSING docs are split
        # by their sub-stage (`processing_status`); when that column is NULL
        # the v1 fallback puts them in the single PROCESSING bucket.
        stage_expr = case(
            (
                WorkflowDocumentORM.status == WorkflowDocumentStatus.UPLOADED.value,
                PipelineStageKey.UPLOAD.value,
            ),
            (
                WorkflowDocumentORM.status == WorkflowDocumentStatus.EXTRACTED.value,
                PipelineStageKey.COMPLETE.value,
            ),
            (
                (WorkflowDocumentORM.status == WorkflowDocumentStatus.PROCESSING.value)
                & (WorkflowDocumentORM.processing_status == _PROCESSING_STATUS_OCR),
                PipelineStageKey.OCR.value,
            ),
            (
                (WorkflowDocumentORM.status == WorkflowDocumentStatus.PROCESSING.value)
                & (WorkflowDocumentORM.processing_status == _PROCESSING_STATUS_EXTRACTION),
                PipelineStageKey.EXTRACTION.value,
            ),
            (
                (WorkflowDocumentORM.status == WorkflowDocumentStatus.PROCESSING.value)
                & (WorkflowDocumentORM.processing_status == _PROCESSING_STATUS_VALIDATION),
                PipelineStageKey.VALIDATION.value,
            ),
            (
                WorkflowDocumentORM.status == WorkflowDocumentStatus.PROCESSING.value,
                PipelineStageKey.PROCESSING.value,
            ),
            else_=None,
        ).label("stage")

        stmt = (
            select(stage_expr, func.count().label("count"))
            .where(WorkflowDocumentORM.tenant_id == tenant_id)
            .group_by(stage_expr)
        )
        rows = (await self.session.execute(stmt)).all()

        counts_by_stage: dict[PipelineStageKey, int] = {}
        for r in rows:
            if r.stage is None:
                # EMPTY / ERROR / other statuses we don't display on the pipeline.
                continue
            counts_by_stage[PipelineStageKey(r.stage)] = int(r.count)

        # Emit only buckets with count > 0, in canonical pipeline order
        # (defined by `PipelineStageKey` enum declaration order).
        return [
            PipelineStage(
                stage=stage,
                label=_STAGE_LABELS[stage],
                count=counts_by_stage[stage],
            )
            for stage in PipelineStageKey
            if counts_by_stage.get(stage, 0) > 0
        ]

    async def list_live_processing(
        self,
        *,
        tenant_id: UUID,
        limit: int,
        avg_processing_seconds: float | None,
        now: datetime,
    ) -> list[LiveProcessingDocument]:
        stmt = (
            select(
                WorkflowDocumentORM.uuid,
                WorkflowDocumentORM.name,
                WorkflowDocumentORM.processing_status,
                WorkflowDocumentORM.created_at,
            )
            .where(
                WorkflowDocumentORM.tenant_id == tenant_id,
                WorkflowDocumentORM.status == WorkflowDocumentStatus.PROCESSING.value,
            )
            .order_by(WorkflowDocumentORM.created_at)
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).all()

        out: list[LiveProcessingDocument] = []
        for r in rows:
            stage = _stage_from_processing_status(r.processing_status)
            started_at = r.created_at
            eta_seconds = _eta_seconds(
                now=now,
                started_at=started_at,
                avg_processing_seconds=avg_processing_seconds,
            )
            out.append(
                LiveProcessingDocument(
                    uuid=r.uuid,
                    name=r.name,
                    stage=stage,
                    progress_pct=_PROGRESS_PCT_BY_STAGE.get(stage, 50),
                    eta_seconds=eta_seconds,
                    started_at=started_at,
                )
            )
        return out


# ---------------------- Pure helpers ----------------------


def _delta_pct(current: int, previous: int) -> float | None:
    """Percentage change current vs. previous; None when previous == 0."""

    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _month_boundaries_utc(now: datetime, time_zone: str) -> tuple[datetime, datetime]:
    """Return (start_of_current_month_utc, start_of_previous_month_utc).

    Both boundaries are computed in the tenant's local timezone and then
    converted to UTC for use in SQL filters against UTC-stored timestamps.
    """

    tz = ZoneInfo(time_zone)
    local_now = now.astimezone(tz)
    start_curr_local = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Previous month: subtract one day from start_of_month, replace day=1.
    prev_month_anchor = start_curr_local.replace(day=1) - _ONE_DAY
    start_prev_local = prev_month_anchor.replace(day=1)
    return start_curr_local.astimezone(UTC), start_prev_local.astimezone(UTC)


def _today_start_utc(now: datetime, time_zone: str) -> datetime:
    tz = ZoneInfo(time_zone)
    local_now = now.astimezone(tz)
    today_local = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_local.astimezone(UTC)


def _months_ago_start(now: datetime, months: int) -> datetime:
    """Start of the bucket (months - 1) months before `now`, in UTC.

    `months=12` from May 2026 returns 2025-06-01 UTC, yielding 12 buckets
    once the current month is included.
    """

    months = max(1, months)
    year = now.year
    month = now.month - (months - 1)
    while month <= 0:
        month += 12
        year -= 1
    return datetime(year, month, 1, tzinfo=UTC)


def _fill_missing_months(
    by_year_month: dict[tuple[int, int], int],
    *,
    now: datetime,
    months: int,
) -> list[ThroughputBucket]:
    """Emit `months` continuous buckets in chronological order, zero-filled."""

    months = max(1, months)
    out: list[ThroughputBucket] = []
    year = now.year
    month = now.month - (months - 1)
    while month <= 0:
        month += 12
        year -= 1
    for _ in range(months):
        out.append(
            ThroughputBucket(
                label=_MONTH_LABELS[month - 1],
                year=year,
                month=month,
                total=by_year_month.get((year, month), 0),
            )
        )
        month += 1
        if month > _MONTHS_IN_YEAR:
            month = 1
            year += 1
    return out


def _eta_seconds(
    *,
    now: datetime,
    started_at: datetime,
    avg_processing_seconds: float | None,
) -> int | None:
    """ETA in seconds based on the global average; None when unknown or overdue.

    No-data (avg is None) and over-budget (elapsed exceeds average) both
    surface as None — the frontend renders "—" in either case.
    """

    if avg_processing_seconds is None:
        return None
    elapsed = max(0.0, (now - started_at).total_seconds())
    remaining = avg_processing_seconds - elapsed
    if remaining <= 0:
        return None
    return int(remaining)


def _stage_from_processing_status(processing_status: str | None) -> PipelineStageKey:
    """Map the raw `processing_status` string to a dashboard stage.

    Returns `PROCESSING` (the v1 fallback) for any value not recognised,
    including NULL. Workers should write one of `_PROCESSING_STATUS_*`
    constants; new strings here are a silent forward-compatibility hint
    rather than an error.
    """

    if processing_status == _PROCESSING_STATUS_OCR:
        return PipelineStageKey.OCR
    if processing_status == _PROCESSING_STATUS_EXTRACTION:
        return PipelineStageKey.EXTRACTION
    if processing_status == _PROCESSING_STATUS_VALIDATION:
        return PipelineStageKey.VALIDATION
    return PipelineStageKey.PROCESSING
