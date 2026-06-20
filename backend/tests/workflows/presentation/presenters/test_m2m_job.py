"""E3 · presenter M2M: merge de capa-1 (parse) y capa-2 (assess) por campo.

`fields` nace de `field_confidence` y cada campo gana `extract_confidence` y
`signals`/`explanation`/`candidates` cuando la fase assess los produjo.
`parse_confidence` se mantiene intacto (D1 §4.4; D2: inline, sin HumanTask).
"""

from __future__ import annotations

from uuid import uuid4

from expects import equal, expect, have_key, have_keys

from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.presentation.presenters.m2m_job import present_document


def _doc(**overrides) -> WorkflowDocument:
    defaults = dict(
        uuid=uuid4(),
        tenant_id=uuid4(),
        field_confidence={
            "rut": {"value": "12.345.678-9", "confidence": 0.9, "source": "bbox"},
            "nombre": {"value": "Juan", "confidence": 0.5, "source": "bbox"},
        },
        extraction={"rut": "12.345.678-9", "nombre": "Juan"},
    )
    defaults.update(overrides)
    return WorkflowDocument(**defaults)


def test_present_document__merges_extract_confidence_keeping_parse():
    doc = _doc(extract_confidence={"rut": 0.97, "nombre": 0.35})

    fields = present_document(doc)["fields"]

    expect(fields["rut"]).to(
        have_keys(value="12.345.678-9", parse_confidence=0.9, extract_confidence=0.97)
    )
    expect(fields["nombre"]).to(have_keys(parse_confidence=0.5, extract_confidence=0.35))


def test_present_document__exposes_signals_and_candidates_for_flagged_fields():
    doc = _doc(
        extract_confidence={"nombre": 0.35},
        signals={
            "nombre": {
                "signals": ["multiple_possible_answers"],
                "explanation": "Hay dos nombres plausibles.",
                "candidates": ["Juan", "Pedro"],
            }
        },
    )

    fields = present_document(doc)["fields"]

    expect(fields["nombre"]).to(
        have_keys(
            signals=["multiple_possible_answers"],
            explanation="Hay dos nombres plausibles.",
            candidates=["Juan", "Pedro"],
        )
    )
    # campo sin señales: no gana claves de assess más allá de extract_confidence
    expect(fields["rut"]).not_to(have_key("signals"))


def test_present_document__without_assess_keeps_layer1_shape():
    doc = _doc()

    fields = present_document(doc)["fields"]

    expect(fields["rut"]).to(equal({"value": "12.345.678-9", "parse_confidence": 0.9, "source": "bbox"}))
    expect(fields["rut"]).not_to(have_key("extract_confidence"))


def test_present_document__assessed_field_missing_from_layer1_still_appears():
    # merge por nombre: si la capa-1 no conoce el campo, se crea el slot
    doc = _doc(field_confidence={}, extract_confidence={"total": 0.8})

    fields = present_document(doc)["fields"]

    expect(fields["total"]).to(
        equal({"value": None, "parse_confidence": None, "source": None, "extract_confidence": 0.8})
    )
