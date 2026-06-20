from unittest.mock import create_autospec
from uuid import uuid4

import pytest

from src.knowledge_base.domain.repositories.kb_document_repository import (
    KBDocumentRepository,
)
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository


@pytest.fixture
def workflow_rule_repository():
    return create_autospec(spec=WorkflowRuleRepository, spec_set=True, instance=True)


@pytest.fixture
def kb_document_repository():
    return create_autospec(spec=KBDocumentRepository, spec_set=True, instance=True)


@pytest.fixture
def workflow_id():
    return uuid4()
