"""Unit tests for the canonical `Citation` model."""

import json
from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.models.processing.citation import Citation


def test_citation__round_trips_through_json():
    doc_id = uuid4()
    citation = Citation(
        document_id=doc_id,
        document_type_slug="dni",
        field_path="emisor.razon_social",
        value="Acme S.A.",
        sub_check_id="c1",
    )

    payload = citation.model_dump(mode="json")
    restored = Citation.model_validate(payload)

    expect(restored).to(equal(citation))
    expect(json.loads(citation.model_dump_json())).to(equal(payload))


def test_citation__optional_fields_default_to_none():
    citation = Citation(
        document_id=uuid4(),
        document_type_slug="dni",
        field_path="rut",
    )

    expect(citation.value).to(be_none)
    expect(citation.sub_check_id).to(be_none)


@pytest.mark.parametrize(
    "missing_field",
    ["document_id", "document_type_slug", "field_path"],
)
def test_citation__rejects_missing_required_field(missing_field):
    payload = {
        "document_id": str(uuid4()),
        "document_type_slug": "dni",
        "field_path": "rut",
    }
    payload.pop(missing_field)

    with pytest.raises(Exception):  # noqa: BLE001
        Citation.model_validate(payload)


def test_citation__is_immutable_frozen():
    citation = Citation(
        document_id=uuid4(),
        document_type_slug="dni",
        field_path="rut",
        value="x",
    )

    with pytest.raises(Exception):  # noqa: BLE001
        citation.value = "y"


def test_citation__document_type_slug_must_be_non_empty():
    with pytest.raises(Exception):  # noqa: BLE001
        Citation(
            document_id=uuid4(),
            document_type_slug="",
            field_path="rut",
        )


def test_citation__field_path_can_be_empty_for_doc_level_refs():
    citation = Citation(
        document_id=uuid4(),
        document_type_slug="dni",
        field_path="",
    )
    expect(citation.field_path).to(equal(""))
