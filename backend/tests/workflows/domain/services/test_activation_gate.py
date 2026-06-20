"""E4 · confidence_gate: evaluación pura de la ActivationPolicy.

Fusión capa-2 (extract_confidence) → capa-1 (field_confidence.confidence),
precedencia de umbrales doctype.campo → campo → default, items camelCase con
signals/candidates(≤3)/page/bbox y etiquetado por documento.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from expects import be_none, equal, expect, have_length

from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.domain.models.policies import ActivationPolicy
from src.workflows.domain.services.activation_gate import (
    evaluate_activation_gate,
    exclude_verified_items,
    flagged_fields_by_document,
)

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_TYPE_FACTURA = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_SLUGS = {_TYPE_FACTURA: "factura"}


def _doc(**overrides) -> WorkflowDocument:
    base = dict(
        uuid=uuid4(),
        tenant_id=_TENANT,
        document_type_id=_TYPE_FACTURA,
        status=WorkflowDocumentStatus.EXTRACTED,
    )
    base.update(overrides)
    return WorkflowDocument(**base)


def test_gate__extract_confidence_layer2_wins_over_field_confidence():
    doc = _doc(
        field_confidence={"total": {"value": "100", "confidence": 0.95, "source": "bbox"}},
        extract_confidence={"total": 0.3},  # capa-2 manda
    )
    policy = ActivationPolicy(field_thresholds={"default": 0.75})

    items = evaluate_activation_gate([doc], _SLUGS, policy)

    expect(items).to(have_length(1))
    expect(items[0]["fieldPath"]).to(equal("total"))
    expect(items[0]["confidence"]).to(equal(0.3))
    expect(items[0]["parseConfidence"]).to(equal(0.95))
    expect(items[0]["extractConfidence"]).to(equal(0.3))


def test_gate__falls_back_to_layer1_when_no_extract_confidence():
    doc = _doc(field_confidence={"total": {"value": "100", "confidence": 0.4, "source": "bbox"}})
    policy = ActivationPolicy(field_thresholds={"default": 0.75})

    items = evaluate_activation_gate([doc], _SLUGS, policy)

    expect(items).to(have_length(1))
    expect(items[0]["confidence"]).to(equal(0.4))
    expect(items[0]["extractConfidence"]).to(be_none)


def test_gate__threshold_precedence_doctype_field_then_field_then_default():
    doc = _doc(
        extract_confidence={"total": 0.6, "fecha": 0.6, "monto": 0.6},
    )
    policy = ActivationPolicy(
        field_thresholds={
            "factura.total": 0.5,  # gana sobre "total" y "default" ⇒ 0.6 pasa
            "fecha": 0.7,  # gana sobre "default" ⇒ 0.6 breachea
            "default": 0.65,  # aplica a "monto" ⇒ 0.6 breachea
        }
    )

    items = evaluate_activation_gate([doc], _SLUGS, policy)

    flagged = sorted(item["fieldPath"] for item in items)
    expect(flagged).to(equal(["fecha", "monto"]))
    by_field = {item["fieldPath"]: item for item in items}
    expect(by_field["fecha"]["threshold"]).to(equal(0.7))
    expect(by_field["monto"]["threshold"]).to(equal(0.65))


def test_gate__field_without_matching_threshold_is_not_evaluated():
    doc = _doc(extract_confidence={"total": 0.1})
    policy = ActivationPolicy(field_thresholds={"otra_cosa": 0.9})  # sin default

    items = evaluate_activation_gate([doc], _SLUGS, policy)

    expect(items).to(equal([]))


def test_gate__items_carry_signals_candidates_capped_page_and_bbox():
    bbox_hit = {"page_number": 2, "polygon": [], "matched_text": "100", "confidence": 0.3}
    doc = _doc(
        extract_confidence={"total": 0.3},
        signals={
            "total": {
                "signals": ["ocr_blur"],
                "candidates": ["100", "700", "麻", "extra"],
            }
        },
        mapped_extraction={"total": {"value": "100", "page_number": 2, "bbox": [bbox_hit]}},
    )
    policy = ActivationPolicy(field_thresholds={"default": 0.75})

    items = evaluate_activation_gate([doc], _SLUGS, policy)

    item = items[0]
    expect(item["documentId"]).to(equal(str(doc.uuid)))
    expect(item["documentType"]).to(equal("factura"))
    expect(item["signals"]).to(equal(["ocr_blur"]))
    expect(item["candidates"]).to(have_length(3))  # cap ≤3
    expect(item["page"]).to(equal(2))
    expect(item["bbox"]).to(equal(bbox_hit))


def test_gate__virtual_docs_without_confidences_are_not_flagged():
    # EXTERNAL_DATA/TOOL nacen sin field_confidence ni extract_confidence:
    # datos validados por el cliente — el gate no los toca.
    doc = _doc(field_confidence=None, extract_confidence=None, mapped_extraction={"total": "100"})
    policy = ActivationPolicy(field_thresholds={"default": 0.99})

    items = evaluate_activation_gate([doc], _SLUGS, policy)

    expect(items).to(equal([]))


def test_gate__skips_non_extracted_documents():
    doc = _doc(status=WorkflowDocumentStatus.PROCESSING, extract_confidence={"total": 0.1})
    policy = ActivationPolicy(field_thresholds={"default": 0.75})

    items = evaluate_activation_gate([doc], _SLUGS, policy)

    expect(items).to(equal([]))


def test_flagged_fields_by_document__groups_field_paths():
    items = [
        {"documentId": "d1", "fieldPath": "total"},
        {"documentId": "d1", "fieldPath": "fecha"},
        {"documentId": "d2", "fieldPath": "monto"},
    ]

    flagged = flagged_fields_by_document(items)

    expect(flagged).to(equal({"d1": ["total", "fecha"], "d2": ["monto"]}))


# ─── E5 §3.1: filtro Rossum del stage L2 ─────────────────────────────────────


def test_exclude_verified__drops_field_paths_verified_at_min_level_or_above():
    items = [
        {"documentId": "d1", "fieldPath": "total"},
        {"documentId": "d1", "fieldPath": "fecha"},
        {"documentId": "d2", "fieldPath": "monto"},
    ]
    verification = {
        "d1": {"total": {"level": 1, "verified_by": "staff:s1"}},  # L1 ⇒ fuera
        "d2": {"monto": {"level": 2, "verified_by": "user:u1"}},  # L2 ⇒ fuera
    }

    filtered = exclude_verified_items(items, verification, min_level=1)

    expect(filtered).to(equal([{"documentId": "d1", "fieldPath": "fecha"}]))


def test_exclude_verified__external_level_0_does_not_count_as_l1():
    items = [{"documentId": "d1", "fieldPath": "total"}]
    verification = {"d1": {"total": {"level": 0, "verified_by": "external"}}}

    filtered = exclude_verified_items(items, verification, min_level=1)

    expect(filtered).to(equal(items))


def test_exclude_verified__documents_without_verification_pass_through():
    items = [{"documentId": "d1", "fieldPath": "total"}]

    expect(exclude_verified_items(items, {}, min_level=1)).to(equal(items))
    expect(exclude_verified_items(items, {"d1": {}}, min_level=1)).to(equal(items))
