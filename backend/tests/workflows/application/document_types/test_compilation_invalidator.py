from unittest.mock import create_autospec
from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.enums.workflow_rules import WorkflowRuleCompilationStatus
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
from src.workflows.application.document_types.compilation_invalidator import (
    DocumentTypeCompilationInvalidator,
)
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.rules.repositories.workflow_rule_compilation import (
    WorkflowRuleCompilationRepository,
)


DOCTYPE_ID = uuid4()
DOCTYPE_SLUG = "cedula_identidad"


@pytest.fixture
def rule_repository():
    return create_autospec(spec=WorkflowRuleRepository, spec_set=True, instance=True)


@pytest.fixture
def compilation_repository():
    return create_autospec(spec=WorkflowRuleCompilationRepository, spec_set=True, instance=True)


def _rule(tenant_id, workflow_id, *, prompt="Una regla sin refs", scope=None, compiled=True) -> WorkflowRule:
    return WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="Rule",
        kind="DERIVATION",
        prompt=prompt,
        scope=scope or {"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        current_compilation_id=uuid4() if compiled else None,
    )


def _compilation(rule: WorkflowRule, artifact: dict | None = None) -> WorkflowRuleCompilation:
    return WorkflowRuleCompilation(
        uuid=rule.current_compilation_id or uuid4(),
        rule_id=rule.uuid,
        version=1,
        kind=rule.kind,
        status=WorkflowRuleCompilationStatus.READY,
        artifact=artifact,
    )


def _invalidator(tenant_id, workflow_id, rule_repository, compilation_repository):
    return DocumentTypeCompilationInvalidator(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_type_id=DOCTYPE_ID,
        document_type_slug=DOCTYPE_SLUG,
        rule_repository=rule_repository,
        compilation_repository=compilation_repository,
    )


async def test_execute__marks_stale_when_scope_references_doctype_uuid(
    tenant_id, rule_repository, compilation_repository
):
    workflow_id = uuid4()
    rule = _rule(
        tenant_id,
        workflow_id,
        scope={"mode": "DOCUMENT_TYPE", "document_type": str(DOCTYPE_ID), "on_empty": "SKIPPED"},
    )
    rule_repository.list_by_workflow.return_value = [rule]

    invalidated = await _invalidator(tenant_id, workflow_id, rule_repository, compilation_repository).execute()

    expect([r.uuid for r in invalidated]).to(equal([rule.uuid]))
    compilation_repository.mark_status.assert_awaited_once_with(
        rule.current_compilation_id,
        WorkflowRuleCompilationStatus.STALE,
    )


async def test_execute__marks_stale_when_prompt_references_doctype_slug(
    tenant_id, rule_repository, compilation_repository
):
    workflow_id = uuid4()
    rule = _rule(tenant_id, workflow_id, prompt=f"Compara @{DOCTYPE_SLUG}.numero con algo")
    rule_repository.list_by_workflow.return_value = [rule]

    invalidated = await _invalidator(tenant_id, workflow_id, rule_repository, compilation_repository).execute()

    expect(len(invalidated)).to(equal(1))
    compilation_repository.mark_status.assert_awaited_once()


async def test_execute__marks_stale_when_compiled_artifact_mentions_slug(
    tenant_id, rule_repository, compilation_repository
):
    workflow_id = uuid4()
    rule = _rule(tenant_id, workflow_id)
    rule_repository.list_by_workflow.return_value = [rule]
    compilation_repository.find_by_id.return_value = _compilation(
        rule,
        artifact={"targets": [{"ref": f"@{DOCTYPE_SLUG}.numero", "doctype": DOCTYPE_SLUG, "path": "numero"}]},
    )

    invalidated = await _invalidator(tenant_id, workflow_id, rule_repository, compilation_repository).execute()

    expect(len(invalidated)).to(equal(1))
    compilation_repository.mark_status.assert_awaited_once()


async def test_execute__skips_rules_without_current_compilation(
    tenant_id, rule_repository, compilation_repository
):
    workflow_id = uuid4()
    rule = _rule(
        tenant_id,
        workflow_id,
        prompt=f"Compara @{DOCTYPE_SLUG}.numero",
        compiled=False,
    )
    rule_repository.list_by_workflow.return_value = [rule]

    invalidated = await _invalidator(tenant_id, workflow_id, rule_repository, compilation_repository).execute()

    expect(invalidated).to(equal([]))
    compilation_repository.mark_status.assert_not_awaited()


async def test_execute__ignores_unrelated_rules(tenant_id, rule_repository, compilation_repository):
    workflow_id = uuid4()
    rule = _rule(tenant_id, workflow_id, prompt="Verifica @otro_tipo.campo")
    rule_repository.list_by_workflow.return_value = [rule]
    compilation_repository.find_by_id.return_value = _compilation(
        rule,
        artifact={"targets": [{"ref": "@otro_tipo.campo", "doctype": "otro_tipo", "path": "campo"}]},
    )

    invalidated = await _invalidator(tenant_id, workflow_id, rule_repository, compilation_repository).execute()

    expect(invalidated).to(equal([]))
    compilation_repository.mark_status.assert_not_awaited()
