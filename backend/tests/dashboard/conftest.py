from unittest.mock import create_autospec

import pytest

from src.dashboard.domain.repositories.dashboard_metrics import (
    DashboardMetricsRepository,
)


@pytest.fixture
def dashboard_metrics_repository():
    return create_autospec(DashboardMetricsRepository, spec_set=True, instance=True)
