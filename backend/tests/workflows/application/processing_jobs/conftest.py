from unittest.mock import create_autospec

import pytest

from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)


@pytest.fixture
def analysis_run_repository():
    return create_autospec(spec=WorkflowAnalysisRunRepository, spec_set=True, instance=True)
