"""E4 · diseño §2: regla estructural de fases en validate_phases.

Todas las fases document-scope deben preceder a la primera case-scope; si la
receta contiene ``await_documents``, debe ser la PRIMERA fase case-scope. La
regla solo se activa cuando el llamador pasa ``phase_scopes`` (el
``PHASE_SCOPES`` del runtime) — el dominio no importa el runtime.
"""

from __future__ import annotations

import pytest
from expects import expect, be_none

from src.workflows.domain.models.pipeline import PhaseSpec
from src.workflows.domain.services.pipeline_validation import (
    InvalidPipelinePhasesError,
    validate_phases,
)

SCOPES = {
    "ingest": "document",
    "extract_text": "document",
    "classify_pages": "document",
    "extract_fields": "document",
    "assess": "document",
    "validate_extraction": "document",
    "finalize": "document",
    "await_documents": "case",
    "extraction_gate": "case",
    "await_clarification": "case",
    "human_review": "case",
    "analyze": "case",
    "output": "case",
    "deliver": "case",
}


def _specs(*kinds: str) -> list[PhaseSpec]:
    return [PhaseSpec(id=f"{kind}-{idx}", kind=kind, config={}) for idx, kind in enumerate(kinds)]


def test_validate_phases__document_before_case_ok():
    result = validate_phases(
        _specs("ingest", "extract_fields", "finalize", "await_documents", "analyze", "deliver"),
        phase_scopes=SCOPES,
    )
    expect(result).to(be_none)


def test_validate_phases__document_after_case_rejected():
    with pytest.raises(InvalidPipelinePhasesError):
        validate_phases(
            _specs("ingest", "await_documents", "extract_fields"),
            phase_scopes=SCOPES,
        )


def test_validate_phases__await_documents_must_be_first_case_scope():
    with pytest.raises(InvalidPipelinePhasesError):
        validate_phases(
            _specs("ingest", "extraction_gate", "await_documents", "analyze"),
            phase_scopes=SCOPES,
        )


def test_validate_phases__case_only_recipe_ok():
    # data-analysis (E3): sin fases document-scope.
    result = validate_phases(_specs("analyze", "output", "deliver"), phase_scopes=SCOPES)
    expect(result).to(be_none)


def test_validate_phases__no_await_documents_no_first_rule():
    result = validate_phases(
        _specs("ingest", "finalize", "extraction_gate", "analyze"),
        phase_scopes=SCOPES,
    )
    expect(result).to(be_none)


def test_validate_phases__rule_inactive_without_scopes():
    # Compat: llamadores E1–E3 sin phase_scopes no ven la regla nueva.
    result = validate_phases(_specs("ingest", "await_documents", "extract_fields"))
    expect(result).to(be_none)


def test_standard_case_recipe__passes_structural_rule():
    from src.workflows.domain.recipes import standard_case_phases

    phases = [PhaseSpec.model_validate(p) for p in standard_case_phases()]
    result = validate_phases(phases, phase_scopes=SCOPES)
    expect(result).to(be_none)
