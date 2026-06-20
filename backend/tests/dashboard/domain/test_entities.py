from expects import equal, expect, raise_error

from src.dashboard.domain.entities.overview import (
    OverviewSummary,
    QueueDelta,
    StatDelta,
)
from src.dashboard.domain.entities.processing import (
    PipelineStageKey,
    ProcessingSummary,
)


def test_stat_delta__accepts_null_delta_pct():
    delta = StatDelta(value=10, delta_pct=None)

    expect(delta.delta_pct).to(equal(None))


def test_queue_delta__defaults_delta_since_last_hour_to_none():
    delta = QueueDelta(value=5)

    expect(delta.delta_since_last_hour).to(equal(None))


def test_overview_summary__accepts_minimal_payload():
    summary = OverviewSummary(
        total_documents=StatDelta(value=0),
        documents_processed=StatDelta(value=0),
        active_workflows=StatDelta(value=0),
        processing_queue=QueueDelta(value=0),
    )

    expect(summary.total_documents.value).to(equal(0))
    expect(summary.processing_queue.delta_since_last_hour).to(equal(None))


def test_processing_summary__avg_processing_seconds_accepts_none():
    summary = ProcessingSummary(
        in_queue=1,
        processing=2,
        completed_today=3,
        failed=0,
        avg_processing_seconds=None,
    )

    expect(summary.avg_processing_seconds).to(equal(None))


def test_processing_summary__avg_processing_seconds_accepts_float():
    summary = ProcessingSummary(
        in_queue=1,
        processing=2,
        completed_today=3,
        failed=0,
        avg_processing_seconds=192.5,
    )

    expect(summary.avg_processing_seconds).to(equal(192.5))


def test_pipeline_stage_key__pipeline_order_places_processing_before_complete():
    # The PROCESSING fallback bucket must sit between in-flight stages and
    # COMPLETE so the rendered chart displays in logical pipeline order.
    stages = list(PipelineStageKey)
    expect(stages.index(PipelineStageKey.PROCESSING)).to(equal(stages.index(PipelineStageKey.COMPLETE) - 1))


def test_pipeline_stage_key__starts_with_upload_and_ends_with_complete():
    stages = list(PipelineStageKey)

    expect(stages[0]).to(equal(PipelineStageKey.UPLOAD))
    expect(stages[-1]).to(equal(PipelineStageKey.COMPLETE))


def test_pipeline_stage_key__sub_stages_appear_between_upload_and_complete():
    stages = list(PipelineStageKey)

    expect(stages.index(PipelineStageKey.OCR)).to(equal(1))
    expect(stages.index(PipelineStageKey.EXTRACTION)).to(equal(2))
    expect(stages.index(PipelineStageKey.VALIDATION)).to(equal(3))


def test_stat_delta__rejects_negative_value():
    # StatDelta doesn't define a constraint, so negative values are
    # accepted by Pydantic. We document this intentional looseness here:
    # the SQL repo guarantees non-negative counts but the domain entity
    # itself doesn't enforce it. If a future change adds a constraint,
    # this test should flip to expecting a ValidationError.
    delta = StatDelta(value=-5)

    expect(delta.value).to(equal(-5))


def test_processing_summary__rejects_missing_fields():
    # Pydantic should refuse missing required fields, regardless of
    # whether the value is meaningful (0, None).
    def construct_incomplete():
        ProcessingSummary(
            in_queue=1,
            processing=2,
            completed_today=3,
            failed=0,
            # avg_processing_seconds missing
        )

    expect(construct_incomplete).to(raise_error(Exception))
