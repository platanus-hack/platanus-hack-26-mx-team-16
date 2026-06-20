from uuid import uuid4

import pytest
from expects import be_a, equal, expect

from src.dashboard.application.use_cases.get_overview import GetOverview
from src.dashboard.domain.entities.overview import (
    OverviewData,
    OverviewSummary,
    QueueDelta,
    StatDelta,
)


@pytest.fixture
def empty_summary():
    return OverviewSummary(
        total_documents=StatDelta(value=0),
        documents_processed=StatDelta(value=0),
        active_workflows=StatDelta(value=0),
        processing_queue=QueueDelta(value=0),
    )


@pytest.fixture
def use_case(dashboard_metrics_repository):
    return GetOverview(
        tenant_id=uuid4(),
        tenant_time_zone="America/Lima",
        throughput_months=12,
        recent_limit=5,
        dashboard_metrics_repository=dashboard_metrics_repository,
    )


async def test_execute__composes_overview_data(use_case, dashboard_metrics_repository, empty_summary):
    dashboard_metrics_repository.get_overview_summary.return_value = empty_summary
    dashboard_metrics_repository.get_throughput.return_value = []
    dashboard_metrics_repository.get_recent_documents.return_value = []

    result = await use_case.execute()

    expect(result).to(be_a(OverviewData))
    expect(result.summary).to(equal(empty_summary))
    expect(result.throughput).to(equal([]))
    expect(result.recent_documents).to(equal([]))


async def test_execute__passes_tenant_id_and_time_zone_to_summary_query(
    use_case, dashboard_metrics_repository, empty_summary
):
    dashboard_metrics_repository.get_overview_summary.return_value = empty_summary
    dashboard_metrics_repository.get_throughput.return_value = []
    dashboard_metrics_repository.get_recent_documents.return_value = []

    await use_case.execute()

    call_kwargs = dashboard_metrics_repository.get_overview_summary.call_args.kwargs
    expect(call_kwargs["tenant_id"]).to(equal(use_case.tenant_id))
    expect(call_kwargs["time_zone"]).to(equal("America/Lima"))


async def test_execute__passes_throughput_months_to_throughput_query(
    use_case, dashboard_metrics_repository, empty_summary
):
    dashboard_metrics_repository.get_overview_summary.return_value = empty_summary
    dashboard_metrics_repository.get_throughput.return_value = []
    dashboard_metrics_repository.get_recent_documents.return_value = []

    await use_case.execute()

    expect(dashboard_metrics_repository.get_throughput.call_args.kwargs["months"]).to(equal(12))


async def test_execute__passes_recent_limit_to_recent_documents_query(
    use_case, dashboard_metrics_repository, empty_summary
):
    dashboard_metrics_repository.get_overview_summary.return_value = empty_summary
    dashboard_metrics_repository.get_throughput.return_value = []
    dashboard_metrics_repository.get_recent_documents.return_value = []

    await use_case.execute()

    expect(dashboard_metrics_repository.get_recent_documents.call_args.kwargs["limit"]).to(equal(5))


async def test_execute__shares_the_same_now_across_sub_queries(use_case, dashboard_metrics_repository, empty_summary):
    dashboard_metrics_repository.get_overview_summary.return_value = empty_summary
    dashboard_metrics_repository.get_throughput.return_value = []
    dashboard_metrics_repository.get_recent_documents.return_value = []

    await use_case.execute()

    summary_now = dashboard_metrics_repository.get_overview_summary.call_args.kwargs["now"]
    throughput_now = dashboard_metrics_repository.get_throughput.call_args.kwargs["now"]
    expect(summary_now).to(equal(throughput_now))
