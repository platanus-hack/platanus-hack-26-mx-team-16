"""Servicio puro de confianza por campo (field_confidence).

El gate de confianza (``confidence_gate``) se consolidó en ``extraction_gate``;
sus tests de handler viven en ``test_case_pause_phases.py``. Aquí queda solo el
servicio puro de confianza por campo.
"""

from __future__ import annotations

from expects import equal, expect

from src.workflows.domain.services.field_confidence import (
    compute_field_confidence,
    fields_needing_clarification,
)


def test_compute_field_confidence__min_of_bbox_with_source():
    mapped = {"name": {"value": "Jane", "bbox": [{"confidence": 0.9}, {"confidence": 0.4}]}}

    result = compute_field_confidence(mapped)

    expect(result["name"]["confidence"]).to(equal(0.4))
    expect(result["name"]["source"]).to(equal("bbox"))
    expect(result["name"]["value"]).to(equal("Jane"))


def test_compute_field_confidence__inferred_leaf_has_no_signal():
    mapped = {"total": {"value": 10, "inferred": True, "bbox": [{"confidence": 0.95}]}}

    result = compute_field_confidence(mapped)

    expect(result["total"]["confidence"]).to(equal(None))
    expect(result["total"]["source"]).to(equal("none"))


def test_fields_needing_clarification__flags_below_threshold_only():
    fc = {
        "low": {"value": "a", "confidence": 0.3, "source": "bbox"},
        "high": {"value": "b", "confidence": 0.95, "source": "bbox"},
        "unknown": {"value": "c", "confidence": None, "source": "none"},
    }

    flagged = fields_needing_clarification(fc, threshold=0.6)

    expect(flagged).to(equal(["low"]))
