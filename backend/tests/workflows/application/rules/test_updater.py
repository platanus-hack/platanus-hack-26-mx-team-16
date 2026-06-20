"""Tests for WorkflowRuleUpdater + invalidation flag (spec §10.2)."""

from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.exceptions.workflow_rules import WorkflowRuleNotFoundError
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.application.workflow_rules.updater import WorkflowRuleUpdater


@pytest.fixture
def existing_rule(tenant_id):
    return WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=uuid4(),
        name="rule",
        kind="VALIDATION",
        prompt="check it",
        config={"severity": "MAJOR"},
        scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        knowledge_refs=[],
    )


@pytest.fixture
def use_case(tenant_id, existing_rule, workflow_rule_repository):
    workflow_rule_repository.find_by_id.return_value = existing_rule
    workflow_rule_repository.update.side_effect = lambda r: r
    return WorkflowRuleUpdater(
        rule_id=existing_rule.uuid,
        tenant_id=tenant_id,
        rule_repository=workflow_rule_repository,
    )


async def test_execute__not_found_raises(use_case, workflow_rule_repository):
    workflow_rule_repository.find_by_id.return_value = None

    with pytest.raises(WorkflowRuleNotFoundError):
        await use_case.execute()


async def test_execute__name_change_does_not_invalidate(use_case):
    use_case.name = "renamed"

    outcome = await use_case.execute()

    expect(outcome.needs_recompilation).to(equal(False))
    expect(outcome.rule.name).to(equal("renamed"))


async def test_execute__severity_change_does_not_invalidate(use_case):
    use_case.config = {"severity": "BLOCKER"}

    outcome = await use_case.execute()

    expect(outcome.needs_recompilation).to(equal(False))


async def test_execute__prompt_change_invalidates(use_case):
    use_case.prompt = "different criterion"

    outcome = await use_case.execute()

    expect(outcome.needs_recompilation).to(equal(True))


async def test_execute__scope_change_invalidates(use_case):
    use_case.scope = {"mode": "SINGLE_DOCUMENT", "document_type": str(uuid4()), "on_empty": "SKIPPED"}

    outcome = await use_case.execute()

    expect(outcome.needs_recompilation).to(equal(True))


async def test_execute__kind_change_invalidates(use_case):
    use_case.kind = "DERIVATION"
    use_case.config = {"output_shape": {"type": "object", "properties": {}}}

    outcome = await use_case.execute()

    expect(outcome.needs_recompilation).to(equal(True))


# ---------------- E5 · `when` por regla ---------------- #


async def test_execute__sets_when_without_invalidating_compilation(use_case):
    use_case.when = '@persona.tipo_entidad == "natural"'

    outcome = await use_case.execute()

    expect(outcome.rule.when).to(equal('@persona.tipo_entidad == "natural"'))
    # `when` se evalúa en runtime: no participa del compilation_input_hash.
    expect(outcome.needs_recompilation).to(equal(False))


async def test_execute__empty_string_clears_when(use_case, existing_rule):
    existing_rule.when = '@persona.tipo_entidad == "natural"'
    use_case.when = ""

    outcome = await use_case.execute()

    expect(outcome.rule.when).to(equal(None))


async def test_execute__none_when_leaves_existing_value_untouched(use_case, existing_rule):
    existing_rule.when = '@persona.tipo_entidad == "natural"'

    outcome = await use_case.execute()

    expect(outcome.rule.when).to(equal('@persona.tipo_entidad == "natural"'))


async def test_execute__invalid_when_raises(use_case):
    from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError

    use_case.when = "esto no es un predicado"

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await use_case.execute()
