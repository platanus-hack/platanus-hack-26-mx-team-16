"""Cálculo puro de completitud del expediente (E4 · diseño §4 · await_documents).

Cuenta documentos EXTRACTED del caso (incluye virtuales EXTERNAL_DATA/TOOL —
"todo dato es un documento") por ``document_type_slug`` contra
``CompletenessPolicy.required_types``. El snapshot resultante se persiste tal
cual en ``workflow_cases.completeness`` y es el shape que consume el FE:
``{satisfied, required, present, missing: [{documentType, missing}]}``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.common.domain.enums.workflows import WorkflowDocumentStatus
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.domain.models.policies import CompletenessPolicy


def compute_case_completeness(
    documents: list[WorkflowDocument],
    slug_by_type_id: dict[UUID, str],
    policy: CompletenessPolicy | None,
) -> dict[str, Any]:
    """Snapshot determinista de completitud.

    Sin policy o ``required_types`` vacío ⇒ ``satisfied=True`` (la espera de
    un ``ready`` explícito la decide el caller — aquí solo se cuenta).
    """
    present: dict[str, int] = {}
    for doc in documents:
        if doc.status != WorkflowDocumentStatus.EXTRACTED:
            continue
        slug = slug_by_type_id.get(doc.document_type_id) if doc.document_type_id else None
        if not slug:
            continue
        present[slug] = present.get(slug, 0) + 1

    required: dict[str, int] = dict(policy.required_types) if policy else {}
    missing: list[dict[str, Any]] = []
    for slug in sorted(required):
        deficit = required[slug] - present.get(slug, 0)
        if deficit > 0:
            missing.append({"documentType": slug, "missing": deficit})

    return {
        "satisfied": not missing,
        "required": required,
        "present": present,
        "missing": missing,
    }
