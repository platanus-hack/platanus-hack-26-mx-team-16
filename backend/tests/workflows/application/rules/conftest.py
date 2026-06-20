from unittest.mock import create_autospec

import pytest

from src.workflows.domain.repositories.document_type import DocumentTypeRepository
from src.workflows.domain.repositories.workflow import WorkflowRepository
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.rules.repositories.workflow_rule_compilation import (
    WorkflowRuleCompilationRepository,
)
from src.workflows.domain.rules.repositories.workflow_rule_result import (
    WorkflowRuleResultRepository,
)
from src.workflows.infrastructure.services.rules import registry
from src.workflows.infrastructure.services.rules.bootstrap import register_stub_kinds


@pytest.fixture(autouse=True)
def _register_kinds():
    """Register stub-backed VALIDATION + DERIVATION kinds for every test.

    The application-layer tests verify the runner/use-case wiring around
    `kind.compile/evaluate`; using `register_stub_kinds` keeps the LLM out
    of the loop so failures point at the application logic, not at LLM noise.
    """
    registry.clear()
    register_stub_kinds()
    yield
    registry.clear()
    register_stub_kinds()


@pytest.fixture
def workflow_rule_repository():
    return create_autospec(spec=WorkflowRuleRepository, spec_set=True, instance=True)


@pytest.fixture
def workflow_rule_compilation_repository():
    return create_autospec(spec=WorkflowRuleCompilationRepository, spec_set=True, instance=True)


@pytest.fixture
def workflow_rule_result_repository():
    return create_autospec(spec=WorkflowRuleResultRepository, spec_set=True, instance=True)


@pytest.fixture
def workflow_repository():
    return create_autospec(spec=WorkflowRepository, spec_set=True, instance=True)


@pytest.fixture
def document_type_repository():
    return create_autospec(spec=DocumentTypeRepository, spec_set=True, instance=True)
