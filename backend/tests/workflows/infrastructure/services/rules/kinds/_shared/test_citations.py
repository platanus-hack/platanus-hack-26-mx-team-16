"""Unit tests for `build_citations`."""

from uuid import uuid4

from expects import be_none, equal, expect

from src.common.domain.models.processing.citation import Citation
from src.workflows.infrastructure.services.rules.kinds._shared.citations import (
    build_citations,
)
from src.workflows.infrastructure.services.rules.kinds._shared.path_resolver import (
    ResolvedValue,
)


def test_build_citations__one_per_resolved_value():
    doc_id = uuid4()
    resolved = [
        ResolvedValue(document_id=doc_id, document_type_slug="dni", field_path="rut", value="12.345.678-5"),
        ResolvedValue(document_id=doc_id, document_type_slug="dni", field_path="nombres", value="Ana"),
    ]

    citations = build_citations(resolved)

    expect(len(citations)).to(equal(2))
    expect(all(isinstance(c, Citation) for c in citations)).to(equal(True))


def test_build_citations__preserves_document_id_and_field_path():
    doc_id = uuid4()
    resolved = [
        ResolvedValue(
            document_id=doc_id, document_type_slug="invoice", field_path="emisor.razon_social", value="Acme S.A."
        ),
    ]

    [citation] = build_citations(resolved)

    expect(citation.document_id).to(equal(doc_id))
    expect(citation.document_type_slug).to(equal("invoice"))
    expect(citation.field_path).to(equal("emisor.razon_social"))
    expect(citation.value).to(equal("Acme S.A."))


def test_build_citations__sub_check_id_propagates_to_each_citation():
    doc_id = uuid4()
    resolved = [
        ResolvedValue(document_id=doc_id, document_type_slug="dni", field_path="rut", value="x"),
        ResolvedValue(document_id=doc_id, document_type_slug="dni", field_path="nombres", value="y"),
    ]

    citations = build_citations(resolved, sub_check_id="c1")

    expect([c.sub_check_id for c in citations]).to(equal(["c1", "c1"]))


def test_build_citations__sub_check_id_defaults_to_none():
    [citation] = build_citations(
        [
            ResolvedValue(document_id=uuid4(), document_type_slug="dni", field_path="rut", value="x"),
        ]
    )

    expect(citation.sub_check_id).to(be_none)


def test_build_citations__stringifies_numeric_value():
    [citation] = build_citations(
        [
            ResolvedValue(document_id=uuid4(), document_type_slug="invoice", field_path="monto_total", value=125000),
        ]
    )

    expect(citation.value).to(equal("125000"))


def test_build_citations__stringifies_bool_value_as_truthy_string():
    [citation] = build_citations(
        [
            ResolvedValue(document_id=uuid4(), document_type_slug="dni", field_path="vigente", value=True),
        ]
    )

    expect(citation.value).to(equal("True"))


def test_build_citations__stringifies_dict_value_as_json():
    [citation] = build_citations(
        [
            ResolvedValue(
                document_id=uuid4(),
                document_type_slug="invoice",
                field_path="emisor.direccion",
                value={"calle": "Apoquindo", "numero": "1234"},
            ),
        ]
    )

    import json

    payload = json.loads(citation.value)
    expect(payload).to(equal({"calle": "Apoquindo", "numero": "1234"}))


def test_build_citations__none_value_stays_none():
    [citation] = build_citations(
        [
            ResolvedValue(document_id=uuid4(), document_type_slug="dni", field_path="fecha_fin", value=None),
        ]
    )

    expect(citation.value).to(be_none)


def test_build_citations__empty_input_returns_empty_list():
    expect(build_citations([])).to(equal([]))
