from datetime import UTC, datetime
from uuid import uuid4

import pytest
from expects import be_none, equal, expect

from src.common.domain.models.processing.document_type import DocumentType
from src.workflows.application.document_processing.input_builder import (
    doctype_to_temporal_dict,
    doctype_versions_from_temporal_dicts,
)


@pytest.fixture
def document_type(tenant_id):
    return DocumentType(
        uuid=uuid4(),
        tenant_id=tenant_id,
        workflow_id=uuid4(),
        name="Cédula de Identidad",
        slug="cedula_identidad",
        description="Documento de identidad",
        fields={"type": "object", "properties": {"numero": {"type": "string"}}},
        validation_rules=[{"id": "v1", "prompt": "algo", "enabled": True}],
        current_version=3,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def test_doctype_to_temporal_dict__seals_slug_and_schema_version(document_type):
    sealed = doctype_to_temporal_dict(document_type)

    expect(sealed["uuid"]).to(equal(str(document_type.uuid)))
    expect(sealed["slug"]).to(equal("cedula_identidad"))
    expect(sealed["schema_version"]).to(equal(3))
    expect(sealed["fields"]).to(equal(document_type.fields))
    expect(sealed["validation_rules"]).to(equal(document_type.validation_rules))


def test_doctype_to_temporal_dict__unversioned_doctype_seals_none(document_type):
    document_type.current_version = None

    sealed = doctype_to_temporal_dict(document_type)

    expect(sealed["schema_version"]).to(be_none)


def test_doctype_versions_from_temporal_dicts__builds_uuid_to_version_map(document_type):
    other = document_type.model_copy(update={"uuid": uuid4(), "current_version": 1})

    sealed = [doctype_to_temporal_dict(document_type), doctype_to_temporal_dict(other)]

    expect(doctype_versions_from_temporal_dicts(sealed)).to(
        equal({str(document_type.uuid): 3, str(other.uuid): 1})
    )


def test_doctype_versions_from_temporal_dicts__skips_unversioned_entries(document_type):
    unversioned = document_type.model_copy(update={"uuid": uuid4(), "current_version": None})

    sealed = [doctype_to_temporal_dict(document_type), doctype_to_temporal_dict(unversioned)]

    expect(doctype_versions_from_temporal_dicts(sealed)).to(
        equal({str(document_type.uuid): 3})
    )
