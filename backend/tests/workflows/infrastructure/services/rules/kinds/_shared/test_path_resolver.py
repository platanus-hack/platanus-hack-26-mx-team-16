"""Unit tests for path_resolver — resolves `DocRef` → `ResolvedValue` list."""

from uuid import uuid4

import pytest
from expects import be_empty, equal, expect, raise_error

from src.workflows.domain.rules.kind_protocol import EvalDocumentInput
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    MissingDocumentError,
    MissingFieldError,
    resolve,
)
from src.workflows.infrastructure.services.rules.kinds._shared.refs import parse_doc_refs


@pytest.fixture
def cedula_doc():
    return EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug="cedula",
        extracted_fields={
            "numero": "12345678",
            "emisor": {"razon_social": "ACME"},
        },
    )


@pytest.fixture
def invoice_doc():
    return EvalDocumentInput(
        document_id=uuid4(),
        document_type_id=uuid4(),
        document_type_slug="invoice",
        extracted_fields={
            "items": [{"subtotal": 100}, {"subtotal": 200}, {"subtotal": 300}],
        },
    )


def test_resolve__scalar_path(cedula_doc):
    ref = parse_doc_refs("@{cedula}.numero")[0]

    resolved = resolve(ref, [cedula_doc])

    expect(len(resolved)).to(equal(1))
    expect(resolved[0].value).to(equal("12345678"))
    expect(resolved[0].field_path).to(equal("numero"))
    expect(resolved[0].document_type_slug).to(equal("cedula"))


def test_resolve__nested_path(cedula_doc):
    ref = parse_doc_refs("@{cedula}.emisor.razon_social")[0]

    resolved = resolve(ref, [cedula_doc])

    expect(resolved[0].value).to(equal("ACME"))
    expect(resolved[0].field_path).to(equal("emisor.razon_social"))


def test_resolve__array_iteration(invoice_doc):
    ref = parse_doc_refs("@{invoice}.items[].subtotal")[0]

    resolved = resolve(ref, [invoice_doc])

    expect([r.value for r in resolved]).to(equal([100, 200, 300]))
    expect(resolved[0].field_path).to(equal("items[0].subtotal"))


def test_resolve__collection_returns_full_extracted_fields(invoice_doc):
    ref = parse_doc_refs("@{invoice}[]")[0]

    resolved = resolve(ref, [invoice_doc])

    expect(len(resolved)).to(equal(1))
    expect(resolved[0].value).to(equal(invoice_doc.extracted_fields))
    expect(resolved[0].field_path).to(equal(""))


def test_resolve__missing_document_raises(cedula_doc):
    ref = parse_doc_refs("@{factura}.numero")[0]

    expect(lambda: resolve(ref, [cedula_doc])).to(raise_error(MissingDocumentError))


def test_resolve__required_missing_field_raises(cedula_doc):
    ref = parse_doc_refs("@{cedula}.fecha_vencimiento")[0]

    expect(lambda: resolve(ref, [cedula_doc])).to(raise_error(MissingFieldError))


def test_resolve__non_required_missing_field_returns_empty(cedula_doc):
    ref = parse_doc_refs("@{cedula}.fecha_vencimiento")[0]

    resolved = resolve(ref, [cedula_doc], required=False)

    expect(resolved).to(be_empty)
