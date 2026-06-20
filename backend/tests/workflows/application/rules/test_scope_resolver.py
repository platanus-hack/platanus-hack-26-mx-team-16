"""Tests for scope_resolver: 4 modes + on_empty behavior (spec §7)."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from expects import equal, expect, have_length

from src.common.domain.enums.workflow_rules import (
    WorkflowRuleOnEmpty,
)
from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.application.workflow_rules.evaluation.scope_resolver import resolve_scope


def _doc(document_type_id: UUID | None) -> WorkflowDocument:
    return WorkflowDocument(
        uuid=uuid4(),
        tenant_id=uuid4(),
        workflow_id=uuid4(),
        workflow_case_id=uuid4(),
        document_type_id=document_type_id,
        name="doc",
        status=WorkflowDocumentStatus.EXTRACTED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_all_documents__single_combo_with_every_doc():
    invoice_type = uuid4()
    receipt_type = uuid4()
    docs = [_doc(invoice_type), _doc(invoice_type), _doc(receipt_type)]

    combos = resolve_scope(
        scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        documents=docs,
        slug_by_document_type={invoice_type: "invoice", receipt_type: "receipt"},
    )

    expect(combos).to(have_length(1))
    expect(combos[0].documents).to(have_length(3))
    expect(combos[0].is_synthetic_empty).to(equal(False))


def test_all_documents__empty_returns_synthetic_skipped():
    combos = resolve_scope(
        scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        documents=[],
        slug_by_document_type={},
    )

    expect(combos).to(have_length(1))
    expect(combos[0].is_synthetic_empty).to(equal(True))
    expect(combos[0].synthetic_outcome).to(equal(WorkflowRuleOnEmpty.SKIPPED))


def test_single_document__one_combo_per_match():
    invoice_type = uuid4()
    other_type = uuid4()
    docs = [_doc(invoice_type), _doc(invoice_type), _doc(other_type)]

    combos = resolve_scope(
        scope={
            "mode": "SINGLE_DOCUMENT",
            "document_type": str(invoice_type),
            "on_empty": "SKIPPED",
        },
        documents=docs,
        slug_by_document_type={invoice_type: "invoice", other_type: "other"},
    )

    expect(combos).to(have_length(2))
    for combo in combos:
        expect(combo.documents).to(have_length(1))
        expect(combo.documents[0].document_type_slug).to(equal("invoice"))


def test_single_document__empty_with_on_empty_failed_synthetic():
    invoice_type = uuid4()
    combos = resolve_scope(
        scope={
            "mode": "SINGLE_DOCUMENT",
            "document_type": str(invoice_type),
            "on_empty": "FAILED",
        },
        documents=[],
        slug_by_document_type={invoice_type: "invoice"},
    )

    expect(combos).to(have_length(1))
    expect(combos[0].is_synthetic_empty).to(equal(True))
    expect(combos[0].synthetic_outcome).to(equal(WorkflowRuleOnEmpty.FAILED))


def test_aggregate_over_type__single_combo_with_all_matching_docs():
    invoice_type = uuid4()
    docs = [_doc(invoice_type), _doc(invoice_type), _doc(uuid4())]

    combos = resolve_scope(
        scope={
            "mode": "AGGREGATE_OVER_TYPE",
            "document_type": str(invoice_type),
            "on_empty": "SKIPPED",
        },
        documents=docs,
        slug_by_document_type={invoice_type: "invoice"},
    )

    expect(combos).to(have_length(1))
    expect(combos[0].documents).to(have_length(2))


def test_tuple_cartesian__produces_n_by_m_combos():
    invoice_type = uuid4()
    receipt_type = uuid4()
    docs = [
        _doc(invoice_type),
        _doc(invoice_type),
        _doc(receipt_type),
        _doc(receipt_type),
        _doc(receipt_type),
    ]

    combos = resolve_scope(
        scope={
            "mode": "TUPLE_CARTESIAN",
            "document_types": [str(invoice_type), str(receipt_type)],
            "on_empty": "SKIPPED",
        },
        documents=docs,
        slug_by_document_type={invoice_type: "invoice", receipt_type: "receipt"},
    )

    expect(combos).to(have_length(6))
    for combo in combos:
        expect(combo.documents).to(have_length(2))


def test_tuple_cartesian__missing_type_yields_synthetic_empty():
    invoice_type = uuid4()
    receipt_type = uuid4()
    docs = [_doc(invoice_type)]  # no receipts

    combos = resolve_scope(
        scope={
            "mode": "TUPLE_CARTESIAN",
            "document_types": [str(invoice_type), str(receipt_type)],
            "on_empty": "PASSED",
        },
        documents=docs,
        slug_by_document_type={invoice_type: "invoice", receipt_type: "receipt"},
    )

    expect(combos).to(have_length(1))
    expect(combos[0].is_synthetic_empty).to(equal(True))
    expect(combos[0].synthetic_outcome).to(equal(WorkflowRuleOnEmpty.PASSED))


def test_combination_hash__stable_for_same_refs():
    invoice_type = uuid4()
    docs = [_doc(invoice_type)]
    a = resolve_scope(
        scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        documents=docs,
        slug_by_document_type={invoice_type: "invoice"},
    )[0]
    b = resolve_scope(
        scope={"mode": "ALL_DOCUMENTS", "on_empty": "SKIPPED"},
        documents=docs,
        slug_by_document_type={invoice_type: "invoice"},
    )[0]

    expect(a.document_refs_hash).to(equal(b.document_refs_hash))
