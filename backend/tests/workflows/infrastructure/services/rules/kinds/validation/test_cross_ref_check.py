"""CROSS_REF_CHECK drift fix (E5): the dispatcher/handler must execute the
shapes the PARSER actually emits (fixtures v4/v6/v10/v11), default the mode,
alias legacy synonyms, and surface configuration errors as
`InvalidWorkflowRuleConfigError` (→ ERRORED) instead of silent FAILs.

Each test goes through `evaluate_sub_check` so substitution (including the
bare `@slug.path` form) and resolution behave exactly like production.
"""

import json
from uuid import uuid4

import pytest
from expects import be_false, be_true, contain, expect

from src.common.domain.exceptions.workflow_rules import InvalidWorkflowRuleConfigError
from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    StaticLLMRunner,
)
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    resolve as resolve_doc_ref,
)
from src.workflows.infrastructure.services.rules.kinds._shared.refs import parse_doc_refs
from src.workflows.infrastructure.services.rules.kinds.validation.dispatcher import (
    evaluate_sub_check,
)


def _doc(slug: str, fields: dict) -> EvalDocumentInput:
    return EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug=slug,
        extracted_fields=fields,
    )


def _resolve_inputs(sub_check: dict, docs: list[EvalDocumentInput]) -> dict[str, list]:
    """Mirror `ValidationKind._resolve_sub_check_inputs`: inputs + param refs."""
    raws = list(sub_check.get("inputs") or [])
    scanned = json.dumps(sub_check.get("params") or {}, ensure_ascii=False)
    for ref in parse_doc_refs(scanned):
        if ref.raw not in raws:
            raws.append(ref.raw)
    out: dict[str, list] = {}
    for raw in raws:
        refs = parse_doc_refs(raw)
        if refs:
            out[raw] = resolve_doc_ref(refs[0], docs)
    return out


async def _run(sub_check, docs, knowledge_context=None):
    return await evaluate_sub_check(
        sub_check,
        resolved_inputs=_resolve_inputs(sub_check, docs),
        resolved_tokens={},
        llm_runner=StaticLLMRunner(payload={}),
        knowledge_context=knowledge_context or [],
    )


# ---------------- lookup shape (fixtures v4 / v11) ---------------- #


_COMUNAS_KB = [{"slug": "comunas_region_metropolitana", "title": "Comunas RM", "content": "Santiago\nÑuñoa\n- Providencia"}]


def _v4_sub_check() -> dict:
    return {
        "id": "c1",
        "method": "CROSS_REF_CHECK",
        "inputs": ["@invoice.emisor.direccion.comuna"],
        "tokens": [],
        "params": {
            "lookup_in": "#comunas_region_metropolitana",
            "match_field": "@invoice.emisor.direccion.comuna",
        },
    }


async def test_cross_ref__v4_lookup_in_kb_list_passes_when_value_present():
    invoice = _doc("invoice", {"emisor": {"direccion": {"comuna": "Ñuñoa"}}})

    result = await _run(_v4_sub_check(), [invoice], knowledge_context=_COMUNAS_KB)

    expect(result.passed).to(be_true)


async def test_cross_ref__v4_lookup_in_kb_list_fails_when_value_absent():
    invoice = _doc("invoice", {"emisor": {"direccion": {"comuna": "Valparaíso"}}})

    result = await _run(_v4_sub_check(), [invoice], knowledge_context=_COMUNAS_KB)

    expect(result.passed).to(be_false)
    expect(result.reason).to(contain("lookup"))


async def test_cross_ref__v11_lookup_with_primary_and_object_items():
    invoice = _doc("invoice", {"emisor": {"rut": "76.123.456-0"}})
    kb = [
        {
            "slug": "giros_sii_por_rut",
            "title": "Giros SII",
            "content": json.dumps(
                [
                    {"rut": "76.123.456-0", "giro_principal": "Venta de alimentos"},
                    {"rut": "77.000.000-K", "giro_principal": "Consultoría"},
                ]
            ),
        }
    ]
    sub_check = {
        "id": "c1",
        "method": "CROSS_REF_CHECK",
        "inputs": ["@invoice.emisor.rut"],
        "tokens": [],
        "params": {
            "primary": "@invoice.emisor.rut",
            "lookup_in": "#giros_sii_por_rut",
            "match_field": "rut",
        },
    }

    result = await _run(sub_check, [invoice], knowledge_context=kb)

    expect(result.passed).to(be_true)


async def test_cross_ref__lookup_with_unknown_kb_slug_raises_config_error():
    invoice = _doc("invoice", {"emisor": {"direccion": {"comuna": "Ñuñoa"}}})

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await _run(_v4_sub_check(), [invoice], knowledge_context=[])


# ---------------- iterator shape (fixtures v6 / v10) ---------------- #


def _v6_sub_check() -> dict:
    return {
        "id": "c1",
        "method": "CROSS_REF_CHECK",
        "inputs": [
            "@dni.nombres",
            "@dni.apellidos",
            "@contract.partes[].nombre",
            "@contract.partes[].rut",
            "@dni.rut",
        ],
        "tokens": [],
        "params": {
            "primary": "concat(@dni.nombres, ' ', @dni.apellidos)",
            "secondary_iterator": "@contract.partes[]",
            "secondary_field": "nombre",
            "normalize": ["lowercase", "strip_accents", "collapse_spaces"],
            "fallback_match": {"field": "rut", "value": "@dni.rut"},
        },
    }


async def test_cross_ref__v6_concat_primary_matches_normalized_party_name():
    dni = _doc("dni", {"nombres": "JOSÉ MIGUEL", "apellidos": "PÉREZ SOTO", "rut": "12.345.678-5"})
    contract = _doc(
        "contract",
        {"partes": [{"nombre": "Jose Miguel Perez Soto", "rut": "9.999.999-9"}]},
    )

    result = await _run(_v6_sub_check(), [dni, contract])

    expect(result.passed).to(be_true)


async def test_cross_ref__v6_falls_back_to_rut_match_when_name_differs():
    dni = _doc("dni", {"nombres": "JOSÉ MIGUEL", "apellidos": "PÉREZ SOTO", "rut": "12.345.678-5"})
    contract = _doc(
        "contract",
        {"partes": [{"nombre": "Otra Persona", "rut": "12.345.678-5"}]},
    )

    result = await _run(_v6_sub_check(), [dni, contract])

    expect(result.passed).to(be_true)
    expect(result.reason).to(contain("fallback"))


async def test_cross_ref__v6_fails_when_neither_name_nor_fallback_match():
    dni = _doc("dni", {"nombres": "JOSÉ MIGUEL", "apellidos": "PÉREZ SOTO", "rut": "12.345.678-5"})
    contract = _doc(
        "contract",
        {"partes": [{"nombre": "Otra Persona", "rut": "9.999.999-9"}]},
    )

    result = await _run(_v6_sub_check(), [dni, contract])

    expect(result.passed).to(be_false)


def _v10_c1_sub_check() -> dict:
    return {
        "id": "c1",
        "method": "CROSS_REF_CHECK",
        "inputs": ["@dni.rut", "@contract.partes[].rut", "@contract.partes[].rol"],
        "tokens": [],
        "params": {
            "primary": "@dni.rut",
            "secondary_iterator": "@contract.partes[]",
            "secondary_field": "rut",
            "filter": {"field": "rol", "op": "in", "value": ["TRABAJADOR", "BENEFICIARIO"]},
        },
    }


async def test_cross_ref__v10_filter_restricts_secondary_items_by_role():
    dni = _doc("dni", {"rut": "12.345.678-5"})
    contract = _doc(
        "contract",
        {
            "partes": [
                {"rut": "12.345.678-5", "rol": "TRABAJADOR"},
                {"rut": "1-9", "rol": "EMPLEADOR"},
            ]
        },
    )

    result = await _run(_v10_c1_sub_check(), [dni, contract])

    expect(result.passed).to(be_true)


async def test_cross_ref__v10_fails_when_match_only_exists_outside_filter():
    dni = _doc("dni", {"rut": "12.345.678-5"})
    contract = _doc(
        "contract",
        {"partes": [{"rut": "12.345.678-5", "rol": "EMPLEADOR"}]},
    )

    result = await _run(_v10_c1_sub_check(), [dni, contract])

    expect(result.passed).to(be_false)


async def test_cross_ref__v10_primary_iterator_with_any_match_predicate():
    payslip_a = _doc("payslip", {"empleador": "ACME LTDA", "monto": 1})
    payslip_b = _doc("payslip", {"empleador": "Otra Empresa", "monto": 2})
    contract = _doc(
        "contract",
        {
            "partes": [
                {"nombre": "Acme Ltda", "rol": "EMPLEADOR"},
                {"nombre": "Juan Pérez", "rol": "TRABAJADOR"},
            ]
        },
    )
    sub_check = {
        "id": "c2",
        "method": "CROSS_REF_CHECK",
        "inputs": ["@payslip.empleador", "@contract.partes[].nombre", "@contract.partes[].rol"],
        "tokens": [],
        "params": {
            "primary_iterator": "@payslip[]",
            "primary_field": "empleador",
            "secondary_iterator": "@contract.partes[]",
            "secondary_field": "nombre",
            "secondary_filter": {"field": "rol", "op": "in", "value": ["EMPLEADOR", "EMPRESA"]},
            "predicate": "ANY_MATCH",
            "normalize": ["lowercase", "strip_accents"],
        },
    }

    result = await _run(sub_check, [payslip_a, payslip_b, contract])

    expect(result.passed).to(be_true)


# ---------------- direct shape: mode default + aliases ---------------- #


def _direct_sub_check(params: dict) -> dict:
    return {
        "id": "c1",
        "method": "CROSS_REF_CHECK",
        "inputs": ["@dni.numero"],
        "tokens": [],
        "params": params,
    }


async def test_cross_ref__mode_defaults_to_equal_and_substitutes_bare_refs():
    dni = _doc("dni", {"numero": "AB-123"})
    pasaporte = _doc("pasaporte", {"numero": "AB-123"})
    sub_check = _direct_sub_check({"against": "@pasaporte.numero"})

    result = await _run(sub_check, [dni, pasaporte])

    expect(result.passed).to(be_true)


async def test_cross_ref__legacy_exact_mode_aliases_to_equal():
    dni = _doc("dni", {"numero": "AB-123"})
    pasaporte = _doc("pasaporte", {"numero": "XY-999"})
    sub_check = _direct_sub_check({"against": "@pasaporte.numero", "mode": "exact"})

    result = await _run(sub_check, [dni, pasaporte])

    expect(result.passed).to(be_false)
    expect(result.reason).to(contain("equal"))


async def test_cross_ref__unknown_mode_raises_config_error():
    dni = _doc("dni", {"numero": "AB-123"})
    pasaporte = _doc("pasaporte", {"numero": "AB-123"})
    sub_check = _direct_sub_check({"against": "@pasaporte.numero", "mode": "fuzzy"})

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await _run(sub_check, [dni, pasaporte])


async def test_cross_ref__missing_target_shape_raises_config_error():
    dni = _doc("dni", {"numero": "AB-123"})
    sub_check = _direct_sub_check({"normalize": ["lowercase"]})

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await _run(sub_check, [dni])


# ---------------- typo'd field params → ERRORED, not silent FAIL (C-minor) ---------------- #


async def test_cross_ref__lookup_match_field_typo_raises_config_error():
    # `match_field: "ruc"` exists in no item key (the field is `rut`) → a config
    # typo. Must raise (ERRORED), not silently report "not found".
    invoice = _doc("invoice", {"emisor": {"rut": "76.123.456-0"}})
    kb = [
        {
            "slug": "giros_sii_por_rut",
            "title": "Giros SII",
            "content": json.dumps([{"rut": "76.123.456-0", "giro_principal": "X"}]),
        }
    ]
    sub_check = {
        "id": "c1",
        "method": "CROSS_REF_CHECK",
        "inputs": ["@invoice.emisor.rut"],
        "tokens": [],
        "params": {
            "primary": "@invoice.emisor.rut",
            "lookup_in": "#giros_sii_por_rut",
            "match_field": "ruc",  # typo: items only carry `rut`/`giro_principal`
        },
    }

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await _run(sub_check, [invoice], knowledge_context=kb)


async def test_cross_ref__iterator_secondary_field_typo_raises_config_error():
    dni = _doc("dni", {"rut": "12.345.678-5"})
    contract = _doc("contract", {"partes": [{"rut": "12.345.678-5", "rol": "TRABAJADOR"}]})
    sub_check = {
        "id": "c1",
        "method": "CROSS_REF_CHECK",
        "inputs": ["@dni.rut", "@contract.partes[].rut"],
        "tokens": [],
        "params": {
            "primary": "@dni.rut",
            "secondary_iterator": "@contract.partes[]",
            "secondary_field": "run",  # typo: items carry `rut`/`rol`
        },
    }

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await _run(sub_check, [dni, contract])


async def test_dispatcher__missing_required_param_surfaces_as_config_error():
    """KeyError on a required param (e.g. CHECKSUM without algorithm) must
    become InvalidWorkflowRuleConfigError (→ ERRORED), not a silent FAIL."""
    dni = _doc("dni", {"numero": "AB-123"})
    sub_check = {
        "id": "c1",
        "method": "CHECKSUM_CHECK",
        "inputs": ["@dni.numero"],
        "tokens": [],
        "params": {},
    }

    with pytest.raises(InvalidWorkflowRuleConfigError):
        await _run(sub_check, [dni])
