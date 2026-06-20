"""Unit tests for the pure helpers inside `sql_dashboard_metrics`.

These helpers are testable without a database; their behaviour drives the
correctness of every metric, so we keep them well-pinned with direct
unit tests instead of relying on end-to-end SQL coverage.
"""

from datetime import UTC, datetime, timedelta

import pytest
from expects import be_none, equal, expect

from src.dashboard.domain.entities.processing import PipelineStageKey
from src.dashboard.infrastructure.repositories.sql_dashboard_metrics import (
    _delta_pct,
    _eta_seconds,
    _fill_missing_months,
    _month_boundaries_utc,
    _months_ago_start,
    _stage_from_processing_status,
    _today_start_utc,
)

# ---------------------- _delta_pct ----------------------


def test_delta_pct__previous_zero_returns_none():
    expect(_delta_pct(current=10, previous=0)).to(be_none)


def test_delta_pct__growth_returns_positive_rounded_to_one_decimal():
    expect(_delta_pct(current=120, previous=100)).to(equal(20.0))


def test_delta_pct__decline_returns_negative():
    expect(_delta_pct(current=80, previous=100)).to(equal(-20.0))


def test_delta_pct__zero_change_returns_zero():
    expect(_delta_pct(current=100, previous=100)).to(equal(0.0))


def test_delta_pct__rounds_to_one_decimal_place():
    expect(_delta_pct(current=110, previous=33)).to(equal(233.3))


# ---------------------- _month_boundaries_utc ----------------------


def test_month_boundaries_utc__lima_timezone_offsets_by_five_hours():
    # America/Lima is UTC-5 (no DST), so midnight Lima = 05:00 UTC.
    now = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)

    curr, prev = _month_boundaries_utc(now=now, time_zone="America/Lima")

    expect(curr).to(equal(datetime(2026, 5, 1, 5, 0, tzinfo=UTC)))
    expect(prev).to(equal(datetime(2026, 4, 1, 5, 0, tzinfo=UTC)))


def test_month_boundaries_utc__utc_timezone_is_a_no_op():
    now = datetime(2026, 3, 15, 18, 30, tzinfo=UTC)

    curr, prev = _month_boundaries_utc(now=now, time_zone="UTC")

    expect(curr).to(equal(datetime(2026, 3, 1, 0, 0, tzinfo=UTC)))
    expect(prev).to(equal(datetime(2026, 2, 1, 0, 0, tzinfo=UTC)))


def test_month_boundaries_utc__january_rolls_back_to_december_of_previous_year():
    now = datetime(2026, 1, 10, 12, 0, tzinfo=UTC)

    _, prev = _month_boundaries_utc(now=now, time_zone="UTC")

    expect(prev).to(equal(datetime(2025, 12, 1, 0, 0, tzinfo=UTC)))


# ---------------------- _today_start_utc ----------------------


def test_today_start_utc__truncates_to_local_midnight_then_converts_to_utc():
    # Lima 2026-05-19 00:00 = UTC 2026-05-19 05:00.
    now = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)

    result = _today_start_utc(now=now, time_zone="America/Lima")

    expect(result).to(equal(datetime(2026, 5, 19, 5, 0, tzinfo=UTC)))


def test_today_start_utc__when_now_is_before_local_midnight_uses_previous_local_day():
    # 03:00 UTC = 22:00 Lima of the PREVIOUS day, so local-day start is
    # 05:00 UTC of the previous day.
    now = datetime(2026, 5, 19, 3, 0, tzinfo=UTC)

    result = _today_start_utc(now=now, time_zone="America/Lima")

    expect(result).to(equal(datetime(2026, 5, 18, 5, 0, tzinfo=UTC)))


# ---------------------- _months_ago_start / _fill_missing_months ----------------------


def test_months_ago_start__twelve_months_returns_first_day_of_11_months_ago():
    # 12-month window from May 2026 includes Jun 2025 → May 2026 (12 buckets).
    now = datetime(2026, 5, 19, tzinfo=UTC)

    result = _months_ago_start(now=now, months=12)

    expect(result).to(equal(datetime(2025, 6, 1, tzinfo=UTC)))


def test_months_ago_start__one_month_returns_current_month_start():
    now = datetime(2026, 5, 19, tzinfo=UTC)

    result = _months_ago_start(now=now, months=1)

    expect(result).to(equal(datetime(2026, 5, 1, tzinfo=UTC)))


def test_months_ago_start__handles_year_boundary():
    # 3-month window from Feb 2026 includes Dec 2025, Jan 2026, Feb 2026.
    now = datetime(2026, 2, 1, tzinfo=UTC)

    result = _months_ago_start(now=now, months=3)

    expect(result).to(equal(datetime(2025, 12, 1, tzinfo=UTC)))


def test_fill_missing_months__emits_continuous_series_zero_filled():
    now = datetime(2026, 5, 19, tzinfo=UTC)
    data = {(2025, 12): 100, (2026, 5): 200}

    buckets = _fill_missing_months(data, now=now, months=6)

    expect(len(buckets)).to(equal(6))
    expect([(b.year, b.month, b.total) for b in buckets]).to(
        equal(
            [
                (2025, 12, 100),
                (2026, 1, 0),
                (2026, 2, 0),
                (2026, 3, 0),
                (2026, 4, 0),
                (2026, 5, 200),
            ]
        )
    )


def test_fill_missing_months__labels_use_three_letter_month_names():
    now = datetime(2026, 3, 15, tzinfo=UTC)

    buckets = _fill_missing_months({}, now=now, months=3)

    expect([b.label for b in buckets]).to(equal(["Jan", "Feb", "Mar"]))


# ---------------------- _eta_seconds ----------------------


def test_eta_seconds__none_avg_returns_none():
    result = _eta_seconds(
        now=datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
        started_at=datetime(2026, 5, 19, 11, 55, tzinfo=UTC),
        avg_processing_seconds=None,
    )

    expect(result).to(be_none)


def test_eta_seconds__under_budget_returns_remaining_seconds():
    now = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    started = now - timedelta(seconds=120)  # 2 min elapsed

    result = _eta_seconds(
        now=now,
        started_at=started,
        avg_processing_seconds=300.0,  # 5 min average
    )

    expect(result).to(equal(180))


def test_eta_seconds__over_budget_returns_none():
    now = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    started = now - timedelta(seconds=500)  # elapsed > avg

    result = _eta_seconds(
        now=now,
        started_at=started,
        avg_processing_seconds=300.0,
    )

    expect(result).to(be_none)


def test_eta_seconds__future_started_at_is_clamped_to_zero_elapsed():
    # Clock skew safety: if `started_at` is in the future for any reason,
    # we should not produce a negative elapsed that inflates the ETA.
    now = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    future_start = now + timedelta(seconds=10)

    result = _eta_seconds(
        now=now,
        started_at=future_start,
        avg_processing_seconds=300.0,
    )

    expect(result).to(equal(300))


# ---------------------- _stage_from_processing_status ----------------------


@pytest.mark.parametrize(
    "processing_status,expected",
    [
        # Lowercase values mirror `DocumentStatus` enum strings actually
        # written by the Temporal activities. Uppercase / unknown strings
        # fall through to the v1 PROCESSING bucket.
        ("ocr", PipelineStageKey.OCR),
        ("extracting", PipelineStageKey.EXTRACTION),
        ("validating", PipelineStageKey.VALIDATION),
        (None, PipelineStageKey.PROCESSING),
        ("", PipelineStageKey.PROCESSING),
        ("EXTRACTION", PipelineStageKey.PROCESSING),
        ("unknown_stage", PipelineStageKey.PROCESSING),
    ],
)
def test_stage_from_processing_status__maps_known_strings_and_falls_back(processing_status, expected):
    expect(_stage_from_processing_status(processing_status)).to(equal(expected))
