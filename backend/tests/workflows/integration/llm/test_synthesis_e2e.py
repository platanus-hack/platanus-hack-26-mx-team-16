"""synthesis E2E real (compile → evaluate → aggregator → synthesizer).

Cases sintéticos pero realistas:

- `kyc_simple`: DNI + utility_bill, KYC pasa.
- `kyc_blocking`: DNI con DV inválido, KYC bloqueado.

Por case:

1. Compila 2 reglas (1 VALIDATION + 1 DERIVATION) con LLM real (PARSER).
2. Evalúa con `extracted_fields` sintéticos y LLM real (sub_check LLM_CHECK).
3. Aggregator (puro) produce el verdict.
4. Synthesizer real produce `summary.output` validado vs `output_schema`.

Asserts críticos:

- `summary.output` válido vs `output_schema`.
- `summary.verdict` igual al verdict computado por el aggregator (no
 alterado por el LLM).
- Para `kyc_blocking`: el verdict es FAIL aunque el LLM "sienta" que el
 documento se ve bien — guardrail "el verdict ya está decidido".
"""

from __future__ import annotations

from uuid import uuid4

import jsonschema
import pytest
from expects import equal, expect

from src.common.domain.enums.run_summary import Verdict
from src.common.domain.enums.workflow_rules import WorkflowRuleResultStatus
from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
from src.common.domain.models.processing.workflow_rule_result import WorkflowRuleResult
from src.workflows.domain.rules.kind_protocol import (
    CompileContext,
    EvalContext,
    EvalDocumentInput,
    EvalInputs,
)
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    AgnoLLMRunner,
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
from tests.workflows.integration.conftest import (
    doctypes_from_slugs,
    llm_default_model,
)


pytestmark = pytest.mark.llm


_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["verdict", "summary_text", "rut_titular"],
    "properties": {
        "verdict": {"type": "string", "enum": ["PASS", "FAIL", "REVIEW"]},
        "summary_text": {"type": "string", "minLength": 10},
        "rut_titular": {"type": "string"},
        "blocking_reasons": {"type": "array", "items": {"type": "string"}},
    },
}


async def _compile_validation(prompt, slugs, *, severity="BLOCKER"):
    tenant_id, workflow_id = uuid4(), uuid4()
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="kyc-rut-validation",
        kind="VALIDATION",
        prompt=prompt,
        config={"severity": severity},
    )
    parser = ValidationParser(llm_runner=AgnoLLMRunner(model_id=llm_default_model()))
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(slugs, workflow_id, tenant_id),
    )
    return rule, await ValidationKind(parser=parser).compile(rule, ctx), ctx


async def _compile_derivation(prompt, slugs, output_shape):
    tenant_id, workflow_id = uuid4(), uuid4()
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="kyc-rut-extract",
        kind="DERIVATION",
        prompt=prompt,
        config={"output_shape": output_shape},
    )
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(slugs, workflow_id, tenant_id),
    )
    kind = DerivationKind(llm_runner=AgnoLLMRunner(model_id=llm_default_model()))
    return rule, kind, await kind.compile(rule, ctx), ctx


def _persist(rule, compilation):
    return WorkflowRuleCompilation(
        uuid=uuid4(),
        rule_id=rule.uuid,
        kind=rule.kind,
        version=1,
        artifact=compilation.artifact,
        compiled_with=compilation.compiled_with,
    )


def _eval_ctx(rule):
    return EvalContext(
        tenant_id=rule.tenant_id,
        workflow_id=rule.workflow_id,
        case_id=uuid4(),
        workflow_analysis_run_id=uuid4(),
    )


def _to_result(rule, outcome, *, run_id, case_id, status=WorkflowRuleResultStatus.SUCCESS):
    return WorkflowRuleResult(
        uuid=uuid4(),
        tenant_id=rule.tenant_id,
        workflow_analysis_run_id=run_id,
        rule_id=rule.uuid,
        case_id=case_id,
        kind=rule.kind,
        status=status,
        output=outcome.output,
        citations=outcome.citations or [],
        evaluation_metadata=outcome.evaluation_metadata or {},
        document_refs_hash="hash",
    )


async def _run_e2e(*, dni_fields):
    val_rule, val_compile, _ = await _compile_validation(
        "El @dni.rut debe estar bien formateado (XX.XXX.XXX-X) y su DV válido según mod 11 chileno.",
        ["dni"],
    )
    der_rule, der_kind, der_compile, _ = await _compile_derivation(
        "Extraer @dni.rut como rut_titular.",
        ["dni"],
        {
            "type": "object",
            "required": ["rut_titular"],
            "properties": {"rut_titular": {"type": "string"}},
        },
    )

    doc = EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug="dni",
        extracted_fields=dni_fields,
    )
    val_kind = ValidationKind(
        parser=ValidationParser(llm_runner=AgnoLLMRunner(model_id=llm_default_model())),
        llm_runner=AgnoLLMRunner(model_id=llm_default_model()),
    )
    val_outcome = await val_kind.evaluate(
        val_rule, _persist(val_rule, val_compile), EvalInputs(documents=[doc]), _eval_ctx(val_rule)
    )
    der_outcome = await der_kind.evaluate(
        der_rule, _persist(der_rule, der_compile), EvalInputs(documents=[doc]), _eval_ctx(der_rule)
    )

    run_id, case_id = uuid4(), uuid4()
    val_result = _to_result(val_rule, val_outcome, run_id=run_id, case_id=case_id)
    der_result = _to_result(der_rule, der_outcome, run_id=run_id, case_id=case_id)

    val_signal = ValidationKind().contribute_to_verdict(val_rule, val_result)
    bundle = verdict_logic.aggregate(
        signals=[val_signal] if val_signal else [],
        results=[val_result, der_result],
    )

    synth = SynthesizerAgent(
        llm_runner=AgnoLLMRunner(model_id=llm_default_model()),
        model=llm_default_model(),
        provider=llm_default_model().split(":", 1)[0],
    )
    summary = await synth.synthesize(
        SynthesizerInput(
            tenant=None,
            verdict=bundle.verdict,
            blocking_failures=[f"rule {val_rule.name}" for s in [val_signal] if s and s.polarity.value == "FAIL"],
            rule_results=[val_result, der_result],
            output_schema=_OUTPUT_SCHEMA,
            synthesis_template=(
                "Genera un resumen ejecutivo del análisis KYC. El verdict ya está "
                "decidido por lógica determinista — NO lo cambies. Usa los outputs "
                "de las reglas para llenar el schema."
            ),
        )
    )
    return bundle, summary


async def test_synthesis_e2e__kyc_simple_summary_is_consistent_with_aggregator():
    """Whatever verdict the aggregator decides for a well-formed RUT, the
    synthesizer must output the SAME verdict — never upgrade or downgrade.
    The DERIVATION output also has to land in the summary unchanged."""
    bundle, summary = await _run_e2e(
        dni_fields={"rut": "12.345.678-5", "nombres": "Ana", "apellidos": "Pérez"},
    )

    jsonschema.validate(instance=summary.output, schema=_OUTPUT_SCHEMA)
    # Key invariant: synthesizer respects the aggregator's verdict.
    expect(summary.output["verdict"]).to(equal(bundle.verdict.value))
    expect(summary.output["rut_titular"]).to(equal("12.345.678-5"))


async def test_synthesis_e2e__kyc_blocking_keeps_fail_verdict_even_under_llm_pressure():
    """Critical guardrail: if validation fails, the synthesizer must NOT
    upgrade the verdict to PASS, even if the LLM finds the document otherwise
    plausible."""
    bundle, summary = await _run_e2e(
        dni_fields={"rut": "AAAAAAAA", "nombres": "Mal", "apellidos": "Formato"},
    )

    jsonschema.validate(instance=summary.output, schema=_OUTPUT_SCHEMA)
    # Aggregator decides FAIL because validation failed.
    expect(bundle.verdict).to(equal(Verdict.FAIL))
    # Synthesizer must respect the aggregator's decision.
    expect(summary.output["verdict"]).to(equal("FAIL"))
