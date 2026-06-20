"""Smoke tests con LLM real (marker `llm` — corre con `make test_llm`).

Subset representativo:

- D1 (extracción simple)
- D4 (clasificación con bandas — usa {{now}})
- V1 (FORMAT + CHECKSUM determinista)
- V3 (OR con AGGREGATE_CHECK)

Cada test:

1. Compila la regla con LLM real (PARSER en VALIDATION; sin LLM en
   DERIVATION compile, pero el evaluate sí usa LLM real).
2. Para DERIVATION: corre `evaluate` con `extracted_fields` sintéticos y
   asserta que `output` es JSON válido contra `output_shape`.
3. Para VALIDATION: asserta que el `parser_response` produce un `tree`
   con `op` AND/OR/NOT y al menos un sub_check.

No comparamos texto literal: solo shape, schema validity y `passed`
cuando hay ground truth obvio.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import jsonschema
import pytest
from expects import be_true, equal, expect

from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.common.domain.models.processing.workflow_rule_compilation import (
    WorkflowRuleCompilation,
)
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
from tests.workflows.integration.conftest import (
    doctypes_from_slugs,
    llm_default_model,
)


pytestmark = pytest.mark.llm


def _runner() -> AgnoLLMRunner:
    return AgnoLLMRunner(model_id=llm_default_model())


def _build_rule(kind: str, prompt: str, config: dict, *, tenant_id, workflow_id) -> WorkflowRule:
    return WorkflowRule(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        name="integration-rule",
        kind=kind,
        prompt=prompt,
        config=config,
    )


def _eval_doc(slug: str, fields: dict) -> EvalDocumentInput:
    return EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug=slug,
        extracted_fields=fields,
    )


def _persist(rule: WorkflowRule, compilation) -> WorkflowRuleCompilation:
    return WorkflowRuleCompilation(
        uuid=uuid4(),
        rule_id=rule.uuid,
        kind=rule.kind,
        version=1,
        artifact=compilation.artifact,
        compiled_with=compilation.compiled_with,
    )


def _eval_ctx(tenant_id, workflow_id) -> EvalContext:
    return EvalContext(
        tenant_id=tenant_id,
        workflow_id=workflow_id,
        case_id=uuid4(),
        workflow_analysis_run_id=uuid4(),
    )


async def test_d1__derivation_extrae_identidad_titular():
    tenant_id, workflow_id = uuid4(), uuid4()
    output_shape = {
        "type": "object",
        "required": ["nombre_completo", "rut"],
        "additionalProperties": False,
        "properties": {
            "nombre_completo": {"type": "string"},
            "rut": {"type": "string"},
        },
    }
    rule = _build_rule(
        "DERIVATION",
        "Extraer el nombre completo (concatenando @dni.nombres y @dni.apellidos) y el RUT del titular: @dni.rut.",
        {"output_shape": output_shape},
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(["dni"], workflow_id, tenant_id),
    )

    kind = DerivationKind(llm_runner=_runner())
    compilation = await kind.compile(rule, ctx)
    persisted = _persist(rule, compilation)

    eval_outcome = await kind.evaluate(
        rule,
        persisted,
        EvalInputs(
            documents=[
                _eval_doc("dni", {"nombres": "Ana María", "apellidos": "Pérez Soto", "rut": "12.345.678-5"}),
            ],
            tokens={},
        ),
        _eval_ctx(tenant_id, workflow_id),
    )

    expect(eval_outcome.error).to(equal(None))
    jsonschema.validate(instance=eval_outcome.output, schema=output_shape)
    expect("Ana" in eval_outcome.output["nombre_completo"]).to(be_true)
    expect(eval_outcome.output["rut"]).to(equal("12.345.678-5"))


async def test_d4__derivation_clasifica_por_bandas_y_token_now():
    tenant_id, workflow_id = uuid4(), uuid4()
    output_shape = {
        "type": "object",
        "required": ["segmento", "ingresos_mensuales", "antiguedad_meses", "justificacion"],
        "properties": {
            "segmento": {"type": "string", "enum": ["BASICO", "MEDIO", "PREMIUM"]},
            "ingresos_mensuales": {"type": "number"},
            "antiguedad_meses": {"type": "integer"},
            "justificacion": {"type": "string"},
        },
    }
    rule = _build_rule(
        "DERIVATION",
        (
            "Determinar el segmento del cliente: BASICO si ingresos < 800000, MEDIO entre 800000 y 2000000, "
            "PREMIUM si > 2000000. Bumpear un nivel si la antigüedad laboral supera 36 meses. "
            "Calcular ingresos como promedio de @payslip.liquido_a_pago y antigüedad desde "
            "@contract.fecha_inicio hasta {{now}}."
        ),
        {"output_shape": output_shape},
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(["payslip", "contract"], workflow_id, tenant_id),
    )
    kind = DerivationKind(llm_runner=_runner())
    compilation = await kind.compile(rule, ctx)
    persisted = _persist(rule, compilation)

    eval_outcome = await kind.evaluate(
        rule,
        persisted,
        EvalInputs(
            documents=[
                _eval_doc("payslip", {"liquido_a_pago": 1_500_000}),
                _eval_doc("contract", {"fecha_inicio": "2024-05-01"}),
            ],
            tokens={"now": datetime(2026, 5, 6, tzinfo=timezone.utc).isoformat()},
        ),
        _eval_ctx(tenant_id, workflow_id),
    )

    expect(eval_outcome.error).to(equal(None))
    jsonschema.validate(instance=eval_outcome.output, schema=output_shape)
    expect(eval_outcome.output["segmento"] in {"BASICO", "MEDIO", "PREMIUM"}).to(be_true)


async def test_v1__validation_compila_a_tree_con_format_y_checksum():
    tenant_id, workflow_id = uuid4(), uuid4()
    rule = _build_rule(
        "VALIDATION",
        "El @dni.rut debe estar bien formateado (XX.XXX.XXX-X) y su dígito verificador debe ser válido según mod 11 chileno.",
        {"severity": "MAJOR"},
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(["dni"], workflow_id, tenant_id),
    )
    parser = ValidationParser(llm_runner=_runner())
    kind = ValidationKind(parser=parser)

    outcome = await kind.compile(rule, ctx)
    artifact = outcome.artifact

    expect("tree" in artifact).to(be_true)
    expect(len(artifact["sub_checks"]) >= 1).to(be_true)
    methods = {sc["method"] for sc in artifact["sub_checks"]}
    expect(methods.issubset({"FORMAT_CHECK", "CHECKSUM_CHECK", "LLM_CHECK"})).to(be_true)
    for sc in artifact["sub_checks"]:
        expect(len(sc["inputs"]) >= 1).to(be_true)
        expect(all(inp.startswith("@") for inp in sc["inputs"])).to(be_true)


async def test_v3__validation_compila_or_con_dos_ramas():
    tenant_id, workflow_id = uuid4(), uuid4()
    rule = _build_rule(
        "VALIDATION",
        (
            "El comprobante de domicilio puede ser: al menos un @utility_bill[] con @utility_bill.fecha_emision "
            "a ≤ 60 días de {{now}}, O al menos un @bank_statement[] con @bank_statement.periodo.hasta "
            "a ≤ 60 días de {{now}}."
        ),
        {"severity": "BLOCKER"},
        tenant_id=tenant_id,
        workflow_id=workflow_id,
    )
    ctx = CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(["utility_bill", "bank_statement"], workflow_id, tenant_id),
    )
    parser = ValidationParser(llm_runner=_runner())
    kind = ValidationKind(parser=parser)

    outcome = await kind.compile(rule, ctx)
    artifact = outcome.artifact

    expect(artifact["tree"].get("op") in {"OR", "AND"} or "ref" in artifact["tree"]).to(be_true)
    serialised = json.dumps(artifact["tree"])
    expect("OR" in serialised).to(be_true)
    expect(len(artifact["sub_checks"]) >= 2).to(be_true)
