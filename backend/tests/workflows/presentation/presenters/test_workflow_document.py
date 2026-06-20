"""E3 · presenter UI de WorkflowDocument: expone capa-2 tal cual (FE la consume)."""

from __future__ import annotations

from uuid import uuid4

from expects import be_none, equal, expect

from src.common.domain.models.processing.workflow_document import WorkflowDocument
from src.workflows.presentation.presenters.workflow_document import (
    WorkflowDocumentPresenter,
)


def test_presenter__exposes_extract_confidence_and_signals_verbatim():
    signals = {
        "nombre": {
            "signals": ["illegible"],
            "explanation": "La zona del nombre está borrosa.",
        }
    }
    doc = WorkflowDocument(
        uuid=uuid4(),
        tenant_id=uuid4(),
        extract_confidence={"nombre": 0.2},
        signals=signals,
    )

    payload = WorkflowDocumentPresenter(instance=doc).to_dict

    expect(payload["extract_confidence"]).to(equal({"nombre": 0.2}))
    expect(payload["signals"]).to(equal(signals))


def test_presenter__null_layer2_stays_null():
    doc = WorkflowDocument(uuid=uuid4(), tenant_id=uuid4())

    payload = WorkflowDocumentPresenter(instance=doc).to_dict

    expect(payload["extract_confidence"]).to(be_none)
    expect(payload["signals"]).to(be_none)
