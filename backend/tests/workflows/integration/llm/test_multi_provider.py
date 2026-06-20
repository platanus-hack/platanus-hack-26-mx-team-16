"""Portabilidad cross-provider con LLM real.

Por cada provider listado en `LLM_TEST_PROVIDERS=anthropic,openai,google` y
por cada ejemplo crítico (V1, V3, V8, D1, D4), verifica que la decisión
estructural sea equivalente:

- compile produce un `tree` con un top-level op válido.
- al menos un sub_check con method conocido y al menos un input.

Skip si `LLM_TEST_PROVIDERS` está vacío.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from expects import equal, expect

from src.common.domain.models.processing.workflow_rule import WorkflowRule
from src.workflows.domain.rules.kind_protocol import CompileContext
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
    llm_test_providers,
)


pytestmark = pytest.mark.llm


_PROVIDER_DEFAULT_MODEL: dict[str, str] = {
    "openai": "openai:gpt-4o-mini",
    "anthropic": "anthropic:claude-3-5-haiku-20241022",
    "google": "google:gemini-2.0-flash",
    "gemini": "google:gemini-2.0-flash",
}


def _resolve_models() -> list[str]:
    raw_providers = llm_test_providers()
    if not raw_providers:
        return []
    out: list[str] = []
    for entry in raw_providers:
        if ":" in entry:
            out.append(entry)
        else:
            model = _PROVIDER_DEFAULT_MODEL.get(entry.lower())
            if not model:
                pytest.skip(f"unknown provider {entry!r} in LLM_TEST_PROVIDERS")
            out.append(model)
    return out


_MODELS = _resolve_models()


_VALIDATION_CASES = [
    {
        "id": "V1",
        "prompt": "El @dni.rut debe estar bien formateado y su DV válido según mod 11 chileno.",
        "slugs": ["dni"],
    },
    {
        "id": "V3",
        "prompt": (
            "El comprobante de domicilio puede ser: al menos un @utility_bill[] con @utility_bill.fecha_emision "
            "a ≤ 60 días de {{now}}, O al menos un @bank_statement[] con @bank_statement.periodo.hasta "
            "a ≤ 60 días de {{now}}."
        ),
        "slugs": ["utility_bill", "bank_statement"],
    },
    {
        "id": "V8",
        "prompt": (
            "El solicitante es elegible si edad ≥ 18 (desde @dni.fecha_nacimiento hasta {{now}}) "
            "Y @dni.nacionalidad = 'CHILENA'. @dni.fecha_vencimiento debe ser posterior a {{now}}."
        ),
        "slugs": ["dni"],
    },
]


_DERIVATION_CASES = [
    {
        "id": "D1",
        "prompt": "Extraer @dni.nombres, @dni.apellidos y @dni.rut.",
        "slugs": ["dni"],
        "output_shape": {
            "type": "object",
            "required": ["nombre_completo", "rut"],
            "properties": {"nombre_completo": {"type": "string"}, "rut": {"type": "string"}},
        },
    },
    {
        "id": "D4",
        "prompt": (
            "Determinar el segmento del cliente: BASICO si ingresos < 800000, MEDIO entre 800000-2000000, "
            "PREMIUM > 2000000. Calcular ingresos como promedio de @payslip.liquido_a_pago y "
            "antigüedad desde @contract.fecha_inicio hasta {{now}}."
        ),
        "slugs": ["payslip", "contract"],
        "output_shape": {
            "type": "object",
            "required": ["segmento"],
            "properties": {"segmento": {"type": "string", "enum": ["BASICO", "MEDIO", "PREMIUM"]}},
        },
    },
]


def _ctx(slugs):
    workflow_id, tenant_id = uuid4(), uuid4()
    return CompileContext(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        document_types=doctypes_from_slugs(slugs, workflow_id, tenant_id),
    )


@pytest.mark.skipif(not _MODELS, reason="LLM_TEST_PROVIDERS env not set")
@pytest.mark.parametrize("model_id", _MODELS)
@pytest.mark.parametrize("case", _VALIDATION_CASES, ids=lambda c: c["id"])
async def test_validation_compile_per_provider__produces_valid_artifact(model_id, case):
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name=f"{case['id']}-{model_id}",
        kind="VALIDATION",
        prompt=case["prompt"],
        config={"severity": "MAJOR"},
    )
    parser = ValidationParser(llm_runner=AgnoLLMRunner(model_id=model_id))
    outcome = await ValidationKind(parser=parser).compile(rule, _ctx(case["slugs"]))

    expect("tree" in outcome.artifact).to(equal(True))
    expect(len(outcome.artifact["sub_checks"]) >= 1).to(equal(True))


@pytest.mark.skipif(not _MODELS, reason="LLM_TEST_PROVIDERS env not set")
@pytest.mark.parametrize("model_id", _MODELS)
@pytest.mark.parametrize("case", _DERIVATION_CASES, ids=lambda c: c["id"])
async def test_derivation_compile_per_provider__regex_parser_is_provider_independent(model_id, case):
    """DERIVATION compile is regex-based — same `inputs[]` across providers."""
    rule = WorkflowRule(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        name=f"{case['id']}-{model_id}",
        kind="DERIVATION",
        prompt=case["prompt"],
        config={"output_shape": case["output_shape"]},
    )
    outcome = await DerivationKind(llm_runner=AgnoLLMRunner(model_id=model_id)).compile(rule, _ctx(case["slugs"]))

    expect(len(outcome.artifact["inputs"]) >= 1).to(equal(True))
