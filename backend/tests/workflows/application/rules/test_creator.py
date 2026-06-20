"""Tests for WorkflowRuleCreator (spec §10.2)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.exceptions.processing import WorkflowNotFoundError
from src.common.domain.exceptions.workflow_rules import (
    InvalidWorkflowRuleConfigError,
    UnknownWorkflowRuleKindError,
)
from src.common.domain.models.processing.workflow import Workflow
from src.workflows.application.workflow_rules.creator import WorkflowRuleCreator


@pytest.fixture
def workflow(tenant_id):
    return Workflow(
        uuid=uuid4(),
        tenant_id=tenant_id,
        name="Workflow",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def use_case(tenant_id, workflow, workflow_rule_repository, workflow_repository):
    workflow_repository.find_by_id.return_value = workflow
    workflow_rule_repository.create.side_effect = lambda r: r
    return WorkflowRuleCreator(
        tenant_id=tenant_id,
        workflow_id=workflow.uuid,
        name="Validar firma",
        kind="VALIDATION",
        prompt="¿La factura tiene firma?",
        rule_repository=workflow_rule_repository,
        workflow_repository=workflow_repository,
    )


async def test_execute__creates_validation_rule_with_default_config(use_case):
    rule = await use_case.execute()

    expect(rule.kind).to(equal("VALIDATION"))
    expect(rule.config["severity"]).to(equal("MAJOR"))
    expect(rule.scope["mode"]).to(equal("ALL_DOCUMENTS"))
    expect(rule.when).to(equal(None))


async def test_execute__stores_normalized_when_predicate(use_case):
    use_case.when = '  @persona.tipo_entidad == "natural"  '

    rule = await use_case.execute()

    expect(rule.when).to(equal('@persona.tipo_entidad == "natural"'))


async def test_execute__invalid_when_predicate_raises(use_case):
    use_case.when = "no es un predicado"

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await use_case.execute()


async def test_execute__workflow_not_found_raises(use_case, workflow_repository):
    workflow_repository.find_by_id.return_value = None

    with pytest.raises(WorkflowNotFoundError):
        await use_case.execute()


async def test_execute__unknown_kind_raises(use_case):
    use_case.kind = "GHOST"

    with pytest.raises(UnknownWorkflowRuleKindError):
        await use_case.execute()


async def test_execute__empty_prompt_raises(use_case):
    use_case.prompt = "   "

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await use_case.execute()


async def test_execute__invalid_severity_raises(use_case):
    use_case.config = {"severity": "WRONG"}

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await use_case.execute()


async def test_execute__derivation_rule_validates_output_shape(
    tenant_id, workflow, workflow_rule_repository, workflow_repository
):
    workflow_repository.find_by_id.return_value = workflow
    workflow_rule_repository.create.side_effect = lambda r: r
    creator = WorkflowRuleCreator(
        tenant_id=tenant_id,
        workflow_id=workflow.uuid,
        name="Total facturado",
        kind="DERIVATION",
        prompt="Suma el total",
        config={"output_shape": {"type": "object", "properties": {"total": {"type": "number"}}}},
        rule_repository=workflow_rule_repository,
        workflow_repository=workflow_repository,
    )

    rule = await creator.execute()

    expect(rule.kind).to(equal("DERIVATION"))
    expect(rule.config["output_shape"]["type"]).to(equal("object"))
