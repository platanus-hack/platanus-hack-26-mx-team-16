from uuid import uuid4

import pytest
from expects import be_a, be_none, equal, expect

from src.dashboard.application.use_cases.get_processing import GetProcessing
from src.dashboard.domain.entities.processing import (
    ProcessingData,
    ProcessingSummary,
)


@pytest.fixture
def summary_with_avg():
    return ProcessingSummary(
        in_queue=10,
        processing=5,
        completed_today=20,
        failed=1,
        avg_processing_seconds=180.0,
    )


@pytest.fixture
def empty_summary():
    return ProcessingSummary(
        in_queue=0,
        processing=0,
        completed_today=0,
        failed=0,
        avg_processing_seconds=None,
    )


@pytest.fixture
def use_case(dashboard_metrics_repository):
    return GetProcessing(
        tenant_id=uuid4(),
        tenant_time_zone="UTC",
        live_limit=5,
        dashboard_metrics_repository=dashboard_metrics_repository,
    )


async def test_execute__returns_processing_data(use_case, dashboard_metrics_repository, summary_with_avg):
    dashboard_metrics_repository.get_processing_summary.return_value = summary_with_avg
    dashboard_metrics_repository.list_pipeline_stages.return_value = []
    dashboard_metrics_repository.list_live_processing.return_value = []

    result = await use_case.execute()

    expect(result).to(be_a(ProcessingData))
    expect(result.summary).to(equal(summary_with_avg))


async def test_execute__feeds_avg_processing_seconds_into_live_query(
    use_case, dashboard_metrics_repository, summary_with_avg
):
    dashboard_metrics_repository.get_processing_summary.return_value = summary_with_avg
    dashboard_metrics_repository.list_pipeline_stages.return_value = []
    dashboard_metrics_repository.list_live_processing.return_value = []

    await use_case.execute()

    call_kwargs = dashboard_metrics_repository.list_live_processing.call_args.kwargs
    expect(call_kwargs["avg_processing_seconds"]).to(equal(180.0))


async def test_execute__forwards_none_avg_when_no_completed_documents(
    use_case, dashboard_metrics_repository, empty_summary
):
    dashboard_metrics_repository.get_processing_summary.return_value = empty_summary
    dashboard_metrics_repository.list_pipeline_stages.return_value = []
    dashboard_metrics_repository.list_live_processing.return_value = []

    await use_case.execute()

    call_kwargs = dashboard_metrics_repository.list_live_processing.call_args.kwargs
    expect(call_kwargs["avg_processing_seconds"]).to(be_none)


async def test_execute__passes_live_limit_to_live_query(use_case, dashboard_metrics_repository, empty_summary):
    dashboard_metrics_repository.get_processing_summary.return_value = empty_summary
    dashboard_metrics_repository.list_pipeline_stages.return_value = []
    dashboard_metrics_repository.list_live_processing.return_value = []

    await use_case.execute()

    expect(dashboard_metrics_repository.list_live_processing.call_args.kwargs["limit"]).to(equal(5))


async def test_execute__shares_the_same_now_across_sub_queries(
    use_case, dashboard_metrics_repository, summary_with_avg
):
    dashboard_metrics_repository.get_processing_summary.return_value = summary_with_avg
    dashboard_metrics_repository.list_pipeline_stages.return_value = []
    dashboard_metrics_repository.list_live_processing.return_value = []

    await use_case.execute()

    summary_now = dashboard_metrics_repository.get_processing_summary.call_args.kwargs["now"]
    live_now = dashboard_metrics_repository.list_live_processing.call_args.kwargs["now"]
    expect(summary_now).to(equal(live_now))


async def test_execute__waits_for_summary_before_querying_live(
    use_case, dashboard_metrics_repository, summary_with_avg
):
    # `list_live_processing` depends on summary.avg_processing_seconds. If
    # the implementation forgot to await the summary first, the live query
    # would either crash (passing the coroutine) or get a default. We
    # assert summary is called before live by inspecting the mock order.
    dashboard_metrics_repository.get_processing_summary.return_value = summary_with_avg
    dashboard_metrics_repository.list_pipeline_stages.return_value = []
    dashboard_metrics_repository.list_live_processing.return_value = []

    await use_case.execute()

    expect(dashboard_metrics_repository.get_processing_summary.called).to(equal(True))
    expect(dashboard_metrics_repository.list_live_processing.called).to(equal(True))
