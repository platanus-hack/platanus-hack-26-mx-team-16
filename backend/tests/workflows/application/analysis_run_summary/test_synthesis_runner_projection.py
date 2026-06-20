"""E2 · SynthesisRunner with x-source projection: pure / mixed / disabled paths."""

from unittest.mock import create_autospec
from uuid import uuid4

import pytest
from expects import be_false, be_none, equal, expect, have_key

from src.common.domain.enums.run_summary import NarrativeStatus
from src.common.domain.models.processing.document_type import DocumentType
from src.common.domain.models.processing.workflow import Workflow
from src.common.domain.models.processing.workflow_analysis_run import WorkflowAnalysisRun
from src.common.domain.models.processing.workflow_analysis_run_summary import (
    WorkflowAnalysisRunSummary,
)
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.application.analysis_run_summary.synthesis_runner import SynthesisRunner
from src.workflows.domain.repositories.workflow_analysis_run import (
    WorkflowAnalysisRunRepository,
)
from src.workflows.domain.rules.repositories.workflow_rule import WorkflowRuleRepository
from src.workflows.domain.rules.repositories.workflow_rule_result import (
    WorkflowRuleResultRepository,
)
from src.workflows.domain.run_summary.errors import SynthesisDisabledError
from src.workflows.domain.run_summary.repositories.run_summary import (
    WorkflowAnalysisRunSummaryRepository,
)
from src.workflows.infrastructure.services.run_summary.synthesizer import (
    SynthesizerAgent,
    SynthesizerOutput,
)

TENANT_ID = uuid4()
WORKFLOW_ID = uuid4()
CASE_ID = uuid4()
RUN_ID = uuid4()
DOC_TYPE_ID = uuid4()

DETERMINISTIC_SCHEMA = {
    "type": "object",
    "properties": {
        "total": {"type": ["number", "null"], "x-source": "@invoice.total"},
        "decision": {"type": "string", "x-source": "{{verdict}}"},
    },
}

MIXED_SCHEMA = {
    "type": "object",
    "properties": {
        "total": {"type": ["number", "null"], "x-source": "@invoice.total"},
        "decision": {"type": "string", "x-source": "{{verdict}}"},
        "summary_text": {"type": "string"},
    },
}


@pytest.fixture
def run_repository():
    return create_autospec(spec=WorkflowAnalysisRunRepository, spec_set=True, instance=True)


@pytest.fixture
def result_repository():
    return create_autospec(spec=WorkflowRuleResultRepository, spec_set=True, instance=True)


@pytest.fixture
def summary_repository():
    return create_autospec(spec=WorkflowAnalysisRunSummaryRepository, spec_set=True, instance=True)


@pytest.fixture
def rule_repository():
    return create_autospec(spec=WorkflowRuleRepository, spec_set=True, instance=True)


@pytest.fixture
def agent():
    return create_autospec(spec=SynthesizerAgent, instance=True)


def _workflow(*, output_schema, synthesis_enabled=True) -> Workflow:
    return Workflow(
        uuid=WORKFLOW_ID,
        tenant_id=TENANT_ID,
        name="W",
        output_schema=output_schema,
        synthesis_enabled=synthesis_enabled,
    )


def _wire(
    repos,
    *,
    workflow: Workflow,
) -> SynthesisRunner:
    (
        workflow_repository,
        run_repository,
        result_repository,
        summary_repository,
        rule_repository,
        document_repository,
        document_type_repository,
        agent,
    ) = repos
    workflow_repository.find_by_id.return_value = workflow
    run_repository.find_by_id.return_value = WorkflowAnalysisRun(
        uuid=RUN_ID, tenant_id=TENANT_ID, workflow_id=WORKFLOW_ID, workflow_case_id=CASE_ID
    )
    summary_repository.find_by_run.return_value = WorkflowAnalysisRunSummary(
        workflow_analysis_run_id=RUN_ID,
        tenant_id=TENANT_ID,
        narrative_status=NarrativeStatus.PENDING,
        input_hash="old",
    )
    result_repository.list_by_run.return_value = []
    document_repository.list_by_case.return_value = [
        WorkflowDocument(
            uuid=uuid4(),
            tenant_id=TENANT_ID,
            workflow_id=WORKFLOW_ID,
            case_id=CASE_ID,
            document_type_id=DOC_TYPE_ID,
            mapped_extraction={"total": {"value": 5, "bbox": []}},
        )
    ]
    document_type_repository.list_by_workflow.return_value = [
        DocumentType(
            uuid=DOC_TYPE_ID,
            tenant_id=TENANT_ID,
            workflow_id=WORKFLOW_ID,
            name="Invoice",
            slug="invoice",
        )
    ]
    rule_repository.list_by_workflow.return_value = []
    return SynthesisRunner(
        run_id=RUN_ID,
        tenant_id=TENANT_ID,
        workflow_repository=workflow_repository,
        run_repository=run_repository,
        result_repository=result_repository,
        summary_repository=summary_repository,
        agent=agent,
        document_repository=document_repository,
        document_type_repository=document_type_repository,
        rule_repository=rule_repository,
    )


async def test_execute__all_fields_resolved_skips_the_agent_entirely(
    workflow_repository,
    run_repository,
    result_repository,
    summary_repository,
    rule_repository,
    document_repository,
    document_type_repository,
    agent,
):
    runner = _wire(
        (
            workflow_repository,
            run_repository,
            result_repository,
            summary_repository,
            rule_repository,
            document_repository,
            document_type_repository,
            agent,
        ),
        workflow=_workflow(output_schema=DETERMINISTIC_SCHEMA),
    )

    await runner.execute()

    agent.synthesize.assert_not_called()
    kwargs = summary_repository.update_narrative.call_args.kwargs
    expect(kwargs["status"]).to(equal(NarrativeStatus.COMPLETED))
    expect(kwargs["output"]).to(equal({"total": 5, "decision": "REVIEW"}))
    expect(kwargs["output_provenance"]).to(have_key("/total"))
    # System tokens carry no citation.
    expect("/decision" in kwargs["output_provenance"]).to(be_false)


async def test_execute__mixed_schema_invokes_agent_and_resolved_fields_win(
    workflow_repository,
    run_repository,
    result_repository,
    summary_repository,
    rule_repository,
    document_repository,
    document_type_repository,
    agent,
):
    runner = _wire(
        (
            workflow_repository,
            run_repository,
            result_repository,
            summary_repository,
            rule_repository,
            document_repository,
            document_type_repository,
            agent,
        ),
        workflow=_workflow(output_schema=MIXED_SCHEMA),
    )
    # The agent hallucinates total/decision — the merge must overwrite them.
    agent.synthesize.return_value = SynthesizerOutput(
        output={"summary_text": "ok", "total": 999, "decision": "PASS"},
        model="m",
        provider="p",
    )

    await runner.execute()

    synthesizer_input = agent.synthesize.call_args.args[0]
    expect(synthesizer_input.resolved_fields).to(equal({"/total": 5, "/decision": "REVIEW"}))
    calls = summary_repository.update_narrative.call_args_list
    expect(calls[0].kwargs["status"]).to(equal(NarrativeStatus.RUNNING))
    final = calls[-1].kwargs
    expect(final["status"]).to(equal(NarrativeStatus.COMPLETED))
    expect(final["output"]).to(equal({"summary_text": "ok", "total": 5, "decision": "REVIEW"}))
    expect(final["output_provenance"]).to(have_key("/total"))


async def test_execute__synthesis_disabled_without_x_source_raises_disabled_error(
    workflow_repository,
    run_repository,
    result_repository,
    summary_repository,
    rule_repository,
    document_repository,
    document_type_repository,
    agent,
):
    # No output_schema → DEFAULT_OUTPUT_SCHEMA (zero x-source) → historic behavior.
    runner = _wire(
        (
            workflow_repository,
            run_repository,
            result_repository,
            summary_repository,
            rule_repository,
            document_repository,
            document_type_repository,
            agent,
        ),
        workflow=_workflow(output_schema=None, synthesis_enabled=False),
    )

    with pytest.raises(SynthesisDisabledError):
        await runner.execute()

    summary_repository.update_narrative.assert_not_called()


async def test_execute__synthesis_disabled_with_x_source_runs_deterministic_path(
    workflow_repository,
    run_repository,
    result_repository,
    summary_repository,
    rule_repository,
    document_repository,
    document_type_repository,
    agent,
):
    # Mixed schema but synthesis off → deterministic fields only, no agent.
    runner = _wire(
        (
            workflow_repository,
            run_repository,
            result_repository,
            summary_repository,
            rule_repository,
            document_repository,
            document_type_repository,
            agent,
        ),
        workflow=_workflow(output_schema=MIXED_SCHEMA, synthesis_enabled=False),
    )

    await runner.execute()

    agent.synthesize.assert_not_called()
    kwargs = summary_repository.update_narrative.call_args.kwargs
    expect(kwargs["status"]).to(equal(NarrativeStatus.COMPLETED))
    expect(kwargs["output"]).to(equal({"total": 5, "decision": "REVIEW"}))
    expect(kwargs["output"].get("summary_text")).to(be_none)
