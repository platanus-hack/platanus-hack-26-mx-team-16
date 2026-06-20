"""Tests for WorkflowRuleCompilationRunner (spec §10.2)."""

from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.enums.workflow_rules import WorkflowRuleCompilationStatus
from src.common.domain.exceptions.workflow_rules import WorkflowRuleNotFoundError
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
from src.workflows.application.workflow_rules.compilation.runner import (
    WorkflowRuleCompilationRunner,
)


@pytest.fixture
def rule(tenant_id):
    return WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=uuid4(),
        name="rule",
        kind="VALIDATION",
        prompt="check",
        config={"severity": "MAJOR"},
        scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
    )


@pytest.fixture
def pending_compilation(rule):
    return WorkflowRuleCompilation(
        uuid=uuid4(),
        rule_id=rule.uuid,
        version=1,
        kind="VALIDATION",
        status=WorkflowRuleCompilationStatus.PENDING,
    )


async def test_execute__missing_rule_raises(
    tenant_id,
    pending_compilation,
    workflow_rule_repository,
    workflow_rule_compilation_repository,
    document_type_repository,
):
    workflow_rule_repository.find_by_id.return_value = None
    runner = WorkflowRuleCompilationRunner(
        compilation_id=pending_compilation.uuid,
        rule_id=uuid4(),
        tenant_id=tenant_id,
        rule_repository=workflow_rule_repository,
        compilation_repository=workflow_rule_compilation_repository,
        document_type_repository=document_type_repository,
    )

    with pytest.raises(WorkflowRuleNotFoundError):
        await runner.execute()


async def test_execute__validation_rule_completes_with_artifact(
    tenant_id,
    rule,
    pending_compilation,
    workflow_rule_repository,
    workflow_rule_compilation_repository,
    document_type_repository,
):
    workflow_rule_repository.find_by_id.return_value = rule
    document_type_repository.list_by_workflow.return_value = []
    workflow_rule_compilation_repository.find_by_id.return_value = pending_compilation

    def _mark(compilation_id, status, **kwargs):
        return pending_compilation.model_copy(
            update={"status": status, "artifact": kwargs.get("artifact"), "compiled_with": kwargs.get("compiled_with")}
        )

    workflow_rule_compilation_repository.mark_status.side_effect = _mark
    workflow_rule_repository.set_current_compilation.side_effect = lambda *_a, **_k: rule

    runner = WorkflowRuleCompilationRunner(
        compilation_id=pending_compilation.uuid,
        rule_id=rule.uuid,
        tenant_id=tenant_id,
        rule_repository=workflow_rule_repository,
        compilation_repository=workflow_rule_compilation_repository,
        document_type_repository=document_type_repository,
    )

    outcome = await runner.execute()

    expect(outcome.status).to(equal(WorkflowRuleCompilationStatus.READY))
    expect(outcome.artifact["prompt"]).to(equal("check"))
    workflow_rule_compilation_repository.mark_status.assert_any_call(
        pending_compilation.uuid, WorkflowRuleCompilationStatus.COMPILING
    )
