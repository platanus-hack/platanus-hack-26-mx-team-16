"""E3 · AssessAgent: parse/clamp del payload LLM + gating de candidates.

El agente es label-only: cualquier payload malformado degrada a resultado
vacío (documento sin assess) — nunca una excepción.
"""

from __future__ import annotations

from expects import be_empty, contain, equal, expect, have_key, have_keys

from src.workflows.infrastructure.services.rules.kinds._shared.llm_runner import (
    FunctionLLMRunner,
    StaticLLMRunner,
)
from src.workflows.infrastructure.services.assess.agent import (
    MAX_CANDIDATES,
    AssessAgent,
    AssessInput,
    parse_assessment,
)


def _inputs(fields: dict | None = None) -> AssessInput:
    return AssessInput(
        fields=fields or {"rut": "12.345.678-9", "nombre": "Juan Pérez"},
        document_text="<!-- PAGE: 1 -->\n\nRUT: 12.345.678-9\nNombre: Juan Pérez",
        document_type_name="Cédula",
    )


# ── parse/clamp ─────────────────────────────────────────────────────────────


def test_parse__clamps_confidence_into_unit_interval():
    payload = {
        "fields": {
            "rut": {"extract_confidence": 1.7},
            "nombre": {"extract_confidence": -0.2},
        }
    }

    result = parse_assessment(payload, expected_fields=["rut", "nombre"])

    expect(result.extract_confidence).to(equal({"rut": 1.0, "nombre": 0.0}))


def test_parse__drops_non_numeric_confidence_and_hallucinated_fields():
    payload = {
        "fields": {
            "rut": {"extract_confidence": "alta"},
            "inventado": {"extract_confidence": 0.9},
            "nombre": {"extract_confidence": 0.8},
        }
    }

    result = parse_assessment(payload, expected_fields=["rut", "nombre"])

    expect(list(result.fields)).to(equal(["nombre"]))


def test_parse__filters_unknown_signals_and_keeps_spanish_explanation():
    payload = {
        "fields": {
            "nombre": {
                "extract_confidence": 0.4,
                "signals": ["illegible", "made_up_signal", "illegible"],
                "explanation": "La zona del nombre está borrosa.",
            }
        }
    }

    result = parse_assessment(payload, expected_fields=["nombre"])

    expect(result.fields["nombre"].signals).to(equal(["illegible"]))
    expect(result.signals["nombre"]).to(
        have_keys(signals=["illegible"], explanation="La zona del nombre está borrosa.")
    )


def test_parse__malformed_root_degrades_to_empty_result():
    result = parse_assessment({"unexpected": True}, expected_fields=["rut"])

    expect(result.fields).to(be_empty)
    expect(result.extract_confidence).to(equal({}))


# ── candidates gating ───────────────────────────────────────────────────────


def test_parse__candidates_only_survive_with_multiple_possible_answers():
    payload = {
        "fields": {
            "nombre": {
                "extract_confidence": 0.5,
                "signals": ["answer_may_be_incomplete"],
                "candidates": ["Juan", "Pedro"],
            }
        }
    }

    result = parse_assessment(payload, expected_fields=["nombre"])

    expect(result.fields["nombre"].candidates).to(be_empty)
    expect(result.signals["nombre"]).not_to(have_key("candidates"))


def test_parse__candidates_truncated_to_max():
    payload = {
        "fields": {
            "nombre": {
                "extract_confidence": 0.5,
                "signals": ["multiple_possible_answers"],
                "candidates": ["a", "b", "c", "d", "e"],
            }
        }
    }

    result = parse_assessment(payload, expected_fields=["nombre"])

    expect(result.fields["nombre"].candidates).to(equal(["a", "b", "c"]))
    expect(len(result.fields["nombre"].candidates)).to(equal(MAX_CANDIDATES))


# ── agente ──────────────────────────────────────────────────────────────────


async def test_assess__happy_path_maps_per_field_results():
    agent = AssessAgent(
        llm_runner=StaticLLMRunner(
            payload={
                "fields": {
                    "rut": {"extract_confidence": 0.95},
                    "nombre": {
                        "extract_confidence": 0.4,
                        "signals": ["multiple_possible_answers"],
                        "explanation": "Hay dos nombres plausibles.",
                        "candidates": ["Juan Pérez", "Pedro Pérez"],
                    },
                }
            }
        )
    )

    result = await agent.assess(_inputs())

    expect(result.extract_confidence).to(equal({"rut": 0.95, "nombre": 0.4}))
    expect(result.flagged_fields).to(equal(["nombre"]))
    expect(result.signals).to(
        equal(
            {
                "nombre": {
                    "signals": ["multiple_possible_answers"],
                    "explanation": "Hay dos nombres plausibles.",
                    "candidates": ["Juan Pérez", "Pedro Pérez"],
                }
            }
        )
    )


async def test_assess__llm_failure_degrades_to_empty_result():
    async def boom(**kwargs):
        raise ValueError("LLM response is not JSON")

    agent = AssessAgent(llm_runner=FunctionLLMRunner(fn=boom))

    result = await agent.assess(_inputs())

    expect(result.fields).to(be_empty)


async def test_assess__no_fields_short_circuits_without_llm_call():
    calls: list = []

    async def runner(**kwargs):
        calls.append(kwargs)
        return {"fields": {}}

    agent = AssessAgent(llm_runner=FunctionLLMRunner(fn=runner))

    result = await agent.assess(AssessInput(fields={}, document_text="texto"))

    expect(result.fields).to(be_empty)
    expect(calls).to(be_empty)


async def test_assess__prompt_carries_fields_and_document_text():
    captured: dict = {}

    async def runner(**kwargs):
        captured.update(kwargs)
        return {"fields": {"rut": {"extract_confidence": 1.0}}}

    agent = AssessAgent(llm_runner=FunctionLLMRunner(fn=runner))

    await agent.assess(_inputs())

    expect(captured["user"]).to(contain("12.345.678-9"))
    expect(captured["user"]).to(contain("PAGE: 1"))
    expect(captured["system"]).to(contain("EN ESPAÑOL"))
    expect(captured["output_schema"]["properties"]).to(have_keys("fields"))
