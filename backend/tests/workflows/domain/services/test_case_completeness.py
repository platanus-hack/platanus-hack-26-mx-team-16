"""E4 · await_documents: cálculo puro de completitud del expediente.

Cuenta docs EXTRACTED (incluye virtuales EXTERNAL_DATA/TOOL) por slug vs
``CompletenessPolicy.required_types``; el snapshot es el shape del FE.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from expects import be_false, be_true, equal, expect

from src.common.domain.enums.workflows import WorkflowDocumentSource, WorkflowDocumentStatus
from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.domain.models.policies import CompletenessPolicy
from src.workflows.domain.services.case_completeness import compute_case_completeness

_TENANT = UUID("22222222-2222-2222-2222-222222222222")
_TYPE_ANEXO = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TYPE_EVAL = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

_SLUGS = {_TYPE_ANEXO: "anexo", _TYPE_EVAL: "evaluacion"}


def _doc(
    type_id: UUID | None,
    status: WorkflowDocumentStatus = WorkflowDocumentStatus.EXTRACTED,
    source: WorkflowDocumentSource = WorkflowDocumentSource.SINGLE,
) -> WorkflowDocument:
    return WorkflowDocument(
        uuid=uuid4(),
        tenant_id=_TENANT,
        document_type_id=type_id,
        status=status,
        source=source,
    )


def test_compute__satisfied_when_all_required_present():
    policy = CompletenessPolicy(required_types={"anexo": 1, "evaluacion": 1})
    docs = [_doc(_TYPE_ANEXO), _doc(_TYPE_EVAL)]

    snapshot = compute_case_completeness(docs, _SLUGS, policy)

    expect(snapshot["satisfied"]).to(be_true)
    expect(snapshot["present"]).to(equal({"anexo": 1, "evaluacion": 1}))
    expect(snapshot["missing"]).to(equal([]))
    expect(snapshot["required"]).to(equal({"anexo": 1, "evaluacion": 1}))


def test_compute__missing_reports_deficit_per_required_type():
    policy = CompletenessPolicy(required_types={"anexo": 2, "evaluacion": 1})
    docs = [_doc(_TYPE_ANEXO)]

    snapshot = compute_case_completeness(docs, _SLUGS, policy)

    expect(snapshot["satisfied"]).to(be_false)
    expect(snapshot["missing"]).to(
        equal(
            [
                {"documentType": "anexo", "missing": 1},
                {"documentType": "evaluacion", "missing": 1},
            ]
        )
    )


def test_compute__virtual_documents_count_toward_completeness():
    # "Todo dato es un documento": EXTERNAL_DATA/TOOL nacen EXTRACTED y cuentan.
    policy = CompletenessPolicy(required_types={"anexo": 1, "evaluacion": 1})
    docs = [
        _doc(_TYPE_ANEXO, source=WorkflowDocumentSource.EXTERNAL_DATA),
        _doc(_TYPE_EVAL, source=WorkflowDocumentSource.TOOL),
    ]

    snapshot = compute_case_completeness(docs, _SLUGS, policy)

    expect(snapshot["satisfied"]).to(be_true)


def test_compute__non_extracted_and_unknown_types_do_not_count():
    policy = CompletenessPolicy(required_types={"anexo": 1})
    docs = [
        _doc(_TYPE_ANEXO, status=WorkflowDocumentStatus.PROCESSING),  # aún no
        _doc(None),  # sin doc type (bucket "Otros")
        _doc(uuid4()),  # tipo fuera del catálogo del workflow
    ]

    snapshot = compute_case_completeness(docs, _SLUGS, policy)

    expect(snapshot["satisfied"]).to(be_false)
    expect(snapshot["present"]).to(equal({}))


def test_compute__no_policy_or_empty_required_is_satisfied():
    docs = [_doc(_TYPE_ANEXO)]

    without_policy = compute_case_completeness(docs, _SLUGS, None)
    empty_required = compute_case_completeness(docs, _SLUGS, CompletenessPolicy())

    expect(without_policy["satisfied"]).to(be_true)
    expect(without_policy["required"]).to(equal({}))
    expect(empty_required["satisfied"]).to(be_true)
    # present sigue informando lo que hay, aunque nada sea requerido
    expect(empty_required["present"]).to(equal({"anexo": 1}))
