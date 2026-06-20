"""E2 · spec case-output §4.0: per-document output (BuildDocumentOutputs)."""

from types import SimpleNamespace
from unittest.mock import create_autospec
from uuid import uuid4

import pytest
from expects import be_none, equal, expect, have_key, have_len

from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.application.analysis_run_summary.document_output import BuildDocumentOutputs
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.rules.repositories.workflow_rule_result import (
    WorkflowRuleResultRepository,
)

TENANT_ID = uuid4()
WORKFLOW_ID = uuid4()
CASE_ID = uuid4()
RUN_ID = uuid4()


@pytest.fixture
def rule_repository():
    return create_autospec(spec=WorkflowRuleRepository, spec_set=True, instance=True)


@pytest.fixture
def result_repository():
    return create_autospec(spec=WorkflowRuleResultRepository, spec_set=True, instance=True)


def _document(document_type_id, mapped_extraction) -> WorkflowDocument:
    return WorkflowDocument(
        uuid=uuid4(),
        tenant_id=TENANT_ID,
        workflow_id=WORKFLOW_ID,
        case_id=CASE_ID,
        document_type_id=document_type_id,
        mapped_extraction=mapped_extraction,
    )


def _use_case(document_repository, document_type_repository, rule_repository, result_repository):
    return BuildDocumentOutputs(
        run_id=RUN_ID,
        case_id=CASE_ID,
        workflow_id=WORKFLOW_ID,
        tenant_id=TENANT_ID,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        rule_repository=rule_repository,
        result_repository=result_repository,
    )


async def test_execute__without_schema_persists_mapped_extraction_with_self_provenance(
    document_repository, document_type_repository, rule_repository, result_repository
):
    dt_id = uuid4()
    doc = _document(dt_id, {"name": {"value": "Ana", "bbox": []}})
    document_repository.list_by_case.return_value = [doc]
    document_repository.update.side_effect = lambda d: d
    # DocumentType without `output_schema` (field lands in a parallel change).
    document_type_repository.list_by_workflow.return_value = [
        SimpleNamespace(uuid=dt_id, slug="cv")
    ]
    rule_repository.list_by_workflow.return_value = []
    result_repository.list_by_run.return_value = []

    updated = await _use_case(
        document_repository, document_type_repository, rule_repository, result_repository
    ).execute()

    expect(updated).to(have_len(1))
    expect(updated[0].output).to(equal({"name": {"value": "Ana", "bbox": []}}))
    citation = updated[0].output_provenance["/name"][0]
    expect(citation["document_id"]).to(equal(str(doc.uuid)))
    expect(citation["document_type_slug"]).to(equal("cv"))
    expect(citation["field_path"]).to(equal("name"))
    expect(citation["value"]).to(equal("Ana"))


async def test_execute__with_schema_projects_deterministically_and_persists_provenance(
    document_repository, document_type_repository, rule_repository, result_repository
):
    dt_id = uuid4()
    doc = _document(dt_id, {"total": {"value": 5, "bbox": []}})
    rule_id = uuid4()
    schema = {
        "type": "object",
        "properties": {
            "total": {"type": "number", "x-source": "@invoice.total"},
            "approved": {"type": "boolean", "x-source": "@rule.credit_check.passed"},
            "narrative": {"type": "string"},  # LLM field → unsupported per-doc in E2
        },
    }
    document_repository.list_by_case.return_value = [doc]
    document_repository.update.side_effect = lambda d: d
    document_type_repository.list_by_workflow.return_value = [
        SimpleNamespace(uuid=dt_id, slug="invoice", output_schema=schema)
    ]
    rule_repository.list_by_workflow.return_value = [
        SimpleNamespace(uuid=rule_id, slug="credit_check")
    ]
    result_repository.list_by_run.return_value = [
        WorkflowRuleResult(
            tenant_id=TENANT_ID,
            workflow_analysis_run_id=RUN_ID,
            rule_id=rule_id,
            case_id=CASE_ID,
            kind="VALIDATION",
            output={"passed": True},
            document_refs={"invoice": [str(doc.uuid)]},
            document_refs_hash="h",
        )
    ]

    updated = await _use_case(
        document_repository, document_type_repository, rule_repository, result_repository
    ).execute()

    expect(updated[0].output).to(equal({"total": 5, "approved": True}))
    expect(updated[0].output_provenance).to(have_key("/total"))
    expect(updated[0].output_provenance).to(have_key("/approved"))
    # LLM fields are left out per-document in E2.
    expect(updated[0].output.get("narrative")).to(be_none)


async def test_execute__rules_not_referencing_the_document_are_excluded(
    document_repository, document_type_repository, rule_repository, result_repository
):
    dt_id = uuid4()
    doc = _document(dt_id, {})
    rule_id = uuid4()
    schema = {
        "type": "object",
        "properties": {"approved": {"type": "boolean", "x-source": "@rule.credit_check.passed"}},
    }
    document_repository.list_by_case.return_value = [doc]
    document_repository.update.side_effect = lambda d: d
    document_type_repository.list_by_workflow.return_value = [
        SimpleNamespace(uuid=dt_id, slug="invoice", output_schema=schema)
    ]
    rule_repository.list_by_workflow.return_value = [
        SimpleNamespace(uuid=rule_id, slug="credit_check")
    ]
    result_repository.list_by_run.return_value = [
        WorkflowRuleResult(
            tenant_id=TENANT_ID,
            workflow_analysis_run_id=RUN_ID,
            rule_id=rule_id,
            case_id=CASE_ID,
            kind="VALIDATION",
            output={"passed": True},
            # References a DIFFERENT document.
            document_refs={"invoice": [str(uuid4())]},
            document_refs_hash="h",
        )
    ]

    updated = await _use_case(
        document_repository, document_type_repository, rule_repository, result_repository
    ).execute()

    expect(updated[0].output).to(equal({"approved": None}))


async def test_execute__no_documents_returns_empty_without_loading_types(
    document_repository, document_type_repository, rule_repository, result_repository
):
    document_repository.list_by_case.return_value = []

    updated = await _use_case(
        document_repository, document_type_repository, rule_repository, result_repository
    ).execute()

    expect(updated).to(equal([]))
    document_type_repository.list_by_workflow.assert_not_called()
