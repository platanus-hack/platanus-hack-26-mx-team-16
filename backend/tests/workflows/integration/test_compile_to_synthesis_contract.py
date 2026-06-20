"""contract test compile → evaluate → aggregator → synthesis.

Cross-spec safety net: a workflow with one VALIDATION rule + one DERIVATION
rule goes end-to-end through the synthetic pipeline (StaticLLMRunner) and
we verify the contracts that link the two specs:

- `WorkflowRuleResult.citations` is a list of canonical `Citation` instances.
- `VerdictSignal` emitted by VALIDATION reaches the aggregator with the
 severity that came from `WorkflowRule.config`.
- `SynthesizerAgent` produces an `output` that validates against the
 workflow's `output_schema`.
- `compute_input_hash` excludes `evaluation_metadata`/`reasoning` so LLM
 noise doesn't bust the cache.

No real LLM is invoked — `StaticLLMRunner` payloads simulate the agents.
"""

from __future__ import annotations

import json
from uuid import uuid4

import jsonschema
import pytest
from expects import be_true, equal, expect

from src.common.domain.enums.run_summary import Verdict
from src.common.domain.enums.workflow_rules import (
    WorkflowRuleResultStatus,
    WorkflowRuleSeverity,
    WorkflowRuleVerdictPolarity,
)
from src.common.domain.models.processing.citation import Citation
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.application.analysis_run_summary.hashing import compute_input_hash
from src.workflows.domain.rules.kind_protocol import (
    CompileContext,
    EvalContext,
    EvalDocumentInput,
    EvalInputs,
)
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    StaticLLMRunner,
)
from src.workflows.infrastructure.services.rules.kinds.derivation import DerivationKind
from src.workflows.infrastructure.services.rules.kinds.validation.kind import (
    ValidationKind,
)
from src.workflows.infrastructure.services.rules.kinds.validation.llm_parser import (
    ValidationParser,
)
from src.workflows.infrastructure.services.run_summary import verdict_logic
from src.workflows.infrastructure.services.run_summary.synthesizer import (
    SynthesizerAgent,
    SynthesizerInput,
)
from tests.workflows.integration.conftest import doctypes_from_slugs


_OUTPUT_SCHEMA: dict = {
    "type": "object",
    "required": ["verdict", "summary_text", "rut_extraido"],
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "FAIL", "REVIEW"]},
        "summary_text": {"type": "string"},
        "rut_extraido": {"type": "string"},
    },
}


async def _run_validation(tenant_id, workflow_id, doc):
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="rut-format",
        kind="VALIDATION",
        prompt="El @dni.rut debe estar bien formateado.",
        config={"severity": "BLOCKER"},
    )
    parser_payload = {
        "tree": {"ref": "c1"},
        "sub_checks": [
            {
                "id": "c1",
                "description": "RUT formato",
                "inputs": ["@dni.rut"],
                "method": "FORMAT_CHECK",
                "params": {"regex": r"^\d{1,2}\.\d{3}\.\d{3}-[0-9kK]$"},
            }
        ],
    }
    kind = ValidationKind(parser=ValidationParser(llm_runner=StaticLLMRunner(payload=parser_payload)))
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(["dni"], workflow_id, tenant_id),
    )
    compile_outcome = await kind.compile(rule, ctx)
    persisted = WorkflowRuleCompilation(
        uuid=uuid4(),
        rule_id=rule.uuid,
        kind=rule.kind,
        version=1,
        artifact=compile_outcome.artifact,
        compiled_with=compile_outcome.compiled_with,
    )
    eval_outcome = await kind.evaluate(
        rule,
        persisted,
        EvalInputs(documents=[doc]),
        EvalContext(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            case_id=uuid4(),
            workflow_analysis_run_id=uuid4(),
        ),
    )
    return rule, eval_outcome


async def _run_derivation(tenant_id, workflow_id, doc):
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="rut-extract",
        kind="DERIVATION",
        prompt="Extraer @dni.rut.",
        config={"output_shape": {"type": "object", "required": ["rut"], "properties": {"rut": {"type": "string"}}}},
    )
    kind = DerivationKind(llm_runner=StaticLLMRunner(payload={"rut": "12.345.678-5"}))
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(["dni"], workflow_id, tenant_id),
    )
    compile_outcome = await kind.compile(rule, ctx)
    persisted = WorkflowRuleCompilation(
        uuid=uuid4(),
        rule_id=rule.uuid,
        kind=rule.kind,
        version=1,
        artifact=compile_outcome.artifact,
        compiled_with=compile_outcome.compiled_with,
    )
    eval_outcome = await kind.evaluate(
        rule,
        persisted,
        EvalInputs(documents=[doc]),
        EvalContext(
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            case_id=uuid4(),
            workflow_analysis_run_id=uuid4(),
        ),
    )
    return rule, eval_outcome


def _to_result(rule: WorkflowRule, outcome, *, run_id, case_id) -> WorkflowRuleResult:
    return WorkflowRuleResult(
        uuid=uuid4(),
        tenant_id=rule.tenant_id,
        workflow_analysis_run_id=run_id,
        rule_id=rule.uuid,
        case_id=case_id,
        kind=rule.kind,
        status=WorkflowRuleResultStatus.SUCCESS,
        output=outcome.output,
        citations=outcome.citations or [],
        evaluation_metadata=outcome.evaluation_metadata or {},
        document_refs_hash="hash-1",
    )


async def test_compile_to_synthesis__contract_holds_end_to_end():
    tenant_id, workflow_id = uuid4(), uuid4()
    run_id, case_id = uuid4(), uuid4()
    doc = EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug="dni",
        extracted_fields={"rut": "12.345.678-5"},
    )

    val_rule, val_outcome = await _run_validation(tenant_id, workflow_id, doc)
    der_rule, der_outcome = await _run_derivation(tenant_id, workflow_id, doc)

    val_result = _to_result(val_rule, val_outcome, run_id=run_id, case_id=case_id)
    der_result = _to_result(der_rule, der_outcome, run_id=run_id, case_id=case_id)

    # === Citations contract: list of canonical Citation instances ===
    expect(all(isinstance(c, Citation) for c in der_result.citations)).to(be_true)
    expect(len(der_result.citations) >= 1).to(be_true)
    expect(der_result.citations[0].document_type_slug).to(equal("dni"))
    expect(der_result.citations[0].field_path).to(equal("rut"))

    # === Verdict signal contract: severity flows from rule.config ===
    val_signal = ValidationKind().contribute_to_verdict(val_rule, val_result)
    expect(val_signal).not_to(equal(None))
    expect(val_signal.severity).to(equal(WorkflowRuleSeverity.BLOCKER))
    expect(val_signal.polarity).to(equal(WorkflowRuleVerdictPolarity.PASS))

    # DERIVATION never emits a verdict signal.
    expect(DerivationKind().contribute_to_verdict(der_rule, der_result)).to(equal(None))

    # === Aggregator contract: signals + results → final verdict ===
    bundle = verdict_logic.aggregate(signals=[val_signal], results=[val_result, der_result])
    expect(bundle.verdict).to(equal(Verdict.PASS))

    # === Synthesizer contract: payload validates against output_schema ===
    synthesiser_payload = {
        "verdict": bundle.verdict.value,
        "summary_text": "DNI verificado y RUT extraído.",
        "rut_extraido": der_result.output["rut"],
    }
    agent = SynthesizerAgent(
        llm_runner=StaticLLMRunner(payload=synthesiser_payload),
        model="static",
        provider="static",
    )
    summary = await agent.synthesize(
        SynthesizerInput(
            tenant=None,
            verdict=bundle.verdict,
            blocking_failures=[],
            rule_results=[val_result, der_result],
            output_schema=_OUTPUT_SCHEMA,
            synthesis_template="Render the summary.",
        )
    )
    jsonschema.validate(instance=summary.output, schema=_OUTPUT_SCHEMA)
    expect(summary.output["verdict"]).to(equal("PASS"))
    expect(summary.output["rut_extraido"]).to(equal("12.345.678-5"))


def test_input_hash__excludes_evaluation_metadata_so_cache_survives_llm_noise():
    """If the synthesiser hash depended on evaluation_metadata, every retry
    would bust the cache. forbids that — lock it in."""
    tenant_id, run_id, rule_id = uuid4(), uuid4(), uuid4()
    base = WorkflowRuleResult(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_analysis_run_id=run_id,
        rule_id=rule_id,
        case_id=uuid4(),
        kind="DERIVATION",
        status=WorkflowRuleResultStatus.SUCCESS,
        output={"rut": "12.345.678-5"},
        document_refs_hash="hash",
    )
    noisy = WorkflowRuleResult(
        uuid=base.uuid,
        tenant_id=base.tenant_id,
        workflow_analysis_run_id=base.workflow_analysis_run_id,
        rule_id=base.rule_id,
        case_id=base.case_id,
        kind=base.kind,
        status=base.status,
        output=base.output,
        evaluation_metadata={"raw_payload": {"foo": "bar"}, "tokens_used": 1234},
        reasoning="The model deliberated for a while.",
        document_refs_hash="hash",
    )

    h_clean = compute_input_hash(
        verdict=Verdict.PASS,
        rule_results=[base],
        output_schema=_OUTPUT_SCHEMA,
        synthesis_template="t",
        model="m",
    )
    h_noisy = compute_input_hash(
        verdict=Verdict.PASS,
        rule_results=[noisy],
        output_schema=_OUTPUT_SCHEMA,
        synthesis_template="t",
        model="m",
    )

    expect(h_clean).to(equal(h_noisy))


def test_input_hash__changes_when_output_actually_changes():
    rule_id = uuid4()
    a = WorkflowRuleResult(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_analysis_run_id=uuid4(),
        rule_id=rule_id,
        case_id=uuid4(),
        kind="DERIVATION",
        status=WorkflowRuleResultStatus.SUCCESS,
        output={"rut": "12.345.678-5"},
        document_refs_hash="hash",
    )
    b = WorkflowRuleResult(
        uuid=a.uuid,
        tenant_id=a.tenant_id,
        workflow_analysis_run_id=a.workflow_analysis_run_id,
        rule_id=rule_id,
        case_id=a.case_id,
        kind="DERIVATION",
        status=WorkflowRuleResultStatus.SUCCESS,
        output={"rut": "9.876.543-2"},
        document_refs_hash="hash",
    )

    h_a = compute_input_hash(
        verdict=Verdict.PASS, rule_results=[a], output_schema={}, synthesis_template="", model="m"
    )
    h_b = compute_input_hash(
        verdict=Verdict.PASS, rule_results=[b], output_schema={}, synthesis_template="", model="m"
    )

    expect(h_a).not_to(equal(h_b))
