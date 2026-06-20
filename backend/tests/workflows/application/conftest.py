from unittest.mock import create_autospec

import pytest

from src.storage.domain.repositories.file_repository import FileRepository
from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.pipeline import PipelineRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import (
    WorkflowDocumentRepository,
)
from src.workflows.domain.repositories.workflow_processing_job_repository import (
    WorkflowProcessingJobRepository,
)


@pytest.fixture
def document_repository():
    return create_autospec(spec=WorkflowDocumentRepository, spec_set=True, instance=True)


@pytest.fixture
def document_type_repository():
    return create_autospec(spec=DocumentTypeRepository, spec_set=True, instance=True)


@pytest.fixture
def workflow_repository():
    return create_autospec(spec=WorkflowRepository, spec_set=True, instance=True)


@pytest.fixture
def workflow_case_repository():
    return create_autospec(spec=WorkflowCaseRepository, spec_set=True, instance=True)


@pytest.fixture
def processing_job_repository():
    return create_autospec(spec=WorkflowProcessingJobRepository, spec_set=True, instance=True)


@pytest.fixture
def file_repository():
    return create_autospec(spec=FileRepository, spec_set=True, instance=True)


@pytest.fixture
def pipeline_repository():
    return create_autospec(spec=PipelineRepository, spec_set=True, instance=True)
