"""Synthesizer agent tests with StaticLLMRunner — happy path + schema-violation."""

from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.enums.run_summary import Verdict
from src.common.domain.enums.workflow_rules import WorkflowRuleResultStatus
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.domain.run_summary.errors import SynthesisOutputInvalidError
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    StaticLLMRunner,
)
from src.workflows.infrastructure.services.run_summary.synthesizer import (
    DEFAULT_OUTPUT_SCHEMA,
    DEFAULT_SYNTHESIS_TEMPLATE,
    SynthesizerAgent,
    SynthesizerInput,
)


def _result() -> WorkflowRuleResult:
    return WorkflowRuleResult(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_analysis_run_id=uuid4(),
        rule_id=uuid4(),
        case_id=uuid4(),
        kind="VALIDATION",
        status=WorkflowRuleResultStatus.SUCCESS,
        output={"passed": True, "reason": "ok"},
        document_refs_hash="hash",
    )


async def test_synthesize__returns_payload_when_schema_valid():
    payload = {"verdict": "PASS", "summary_text": "All checks passed."}
    agent = SynthesizerAgent(
        llm_runner=StaticLLMRunner(payload=payload),
        model="gpt-x",
        provider="anthropic",
    )

    outcome = await agent.synthesize(
        SynthesizerInput(
            tenant=None,
            verdict=Verdict.PASS,
            blocking_failures=[],
            rule_results=[_result()],
            output_schema=DEFAULT_OUTPUT_SCHEMA,
            synthesis_template=DEFAULT_SYNTHESIS_TEMPLATE,
        )
    )

    expect(outcome.output).to(equal(payload))
    expect(outcome.model).to(equal("gpt-x"))
    expect(outcome.provider).to(equal("anthropic"))


async def test_synthesize__rejects_payload_missing_required_fields():
    agent = SynthesizerAgent(
        llm_runner=StaticLLMRunner(payload={"verdict": "PASS"})  # missing summary_text
    )

    with pytest.raises(SynthesisOutputInvalidError):
        await agent.synthesize(
            SynthesizerInput(
                tenant=None,
                verdict=Verdict.PASS,
                blocking_failures=[],
                rule_results=[],
                output_schema=DEFAULT_OUTPUT_SCHEMA,
                synthesis_template=DEFAULT_SYNTHESIS_TEMPLATE,
            )
        )


async def test_synthesize__rejects_invalid_verdict_enum_value():
    agent = SynthesizerAgent(llm_runner=StaticLLMRunner(payload={"verdict": "MAYBE", "summary_text": "x"}))

    with pytest.raises(SynthesisOutputInvalidError):
        await agent.synthesize(
            SynthesizerInput(
                tenant=None,
                verdict=Verdict.PASS,
                blocking_failures=[],
                rule_results=[],
                output_schema=DEFAULT_OUTPUT_SCHEMA,
                synthesis_template=DEFAULT_SYNTHESIS_TEMPLATE,
            )
        )
