"""E5: los request models del bench aceptan camelCase (alias) y snake_case.

El middleware camel→snake de requests es un no-op (BaseHTTPMiddleware no puede
reemplazar el body vía ``request._receive``), así que el contrato camelCase se
honra con aliases pydantic — estos tests lo fijan.
"""

from expects import equal, expect

from src.workflows.presentation.endpoints.m2m_corrections import CorrectionFieldItem
from src.workflows.presentation.endpoints.workflow_case_fields import FieldPatchItem


def test_field_patch_item__accepts_camel_alias():
    item = FieldPatchItem.model_validate({"fieldPath": "ci", "action": "correct", "value": "1"})
    expect(item.field_path).to(equal("ci"))


def test_field_patch_item__accepts_snake_too():
    item = FieldPatchItem.model_validate({"field_path": "ci"})
    expect(item.field_path).to(equal("ci"))
    expect(item.action).to(equal("correct"))


def test_correction_field_item__accepts_camel_alias():
    item = CorrectionFieldItem.model_validate(
        {"documentId": "7b4d5cbb-4ee1-4d7e-ad82-8d7a8b429d7a", "fieldPath": "ci", "value": "1"}
    )
    expect(item.field_path).to(equal("ci"))
    expect(str(item.document_id)).to(equal("7b4d5cbb-4ee1-4d7e-ad82-8d7a8b429d7a"))
